import json
import sqlite3
import socket
import threading
from passlib.context import CryptContext

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet

pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
)


def generate_keys():
    """Генерирует приватный и публичный ключи"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    serial_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    serial_pub = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return serial_private, serial_pub


def decrypt(data, key):
    """Дешифрует сообщение, закодированное публичным ключом"""
    private_key = read_private(key)
    decrypted = private_key.decrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted


def read_private(key):
    """Читает приватный ключ"""
    private_key = serialization.load_pem_private_key(
        key,
        password=None,
        backend=default_backend()
    )
    return private_key


class Server:
    """Класс сервера, в котором реализовано подключение, регистрация и
    авторизация клиентов, работа с контактами и сообщениями"""
    def __init__(self):
        """Инициализация класса"""
        self.host = 'localhost'
        self.port = 54321
        self.socket = None
        self.clients = []
        self.logins = {}
        self.coders = {}

    def start(self):
        """Запуск сервера"""
        if self.socket:
            raise RuntimeError('Сервер уже запущен')
        print(f'Сервер запущен по адресу {self.host}:{self.port}')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1024)
        self.socket.settimeout(1000000)
        while True:
            client_socket, address = self.socket.accept()
            t = threading.Thread(target=self.mainloop, args=(client_socket, ))
            t.start()

    def mainloop(self, client_socket):
        """Обработка запросов от клиентов сервера"""
        con = sqlite3.connect("messenger.sql")
        cur = con.cursor()
        self.clients.append(client_socket)

        serial_private, serial_pub = generate_keys()
        client_socket.send(serial_pub)
        key_data = client_socket.recv(1024)
        key = decrypt(key_data, serial_private)
        coder = Fernet(key)
        self.coders[client_socket] = coder

        while True:
            try:
                request = json.loads(coder.decrypt(client_socket.recv(1024)))
                if request['action'] == 'check_online':
                    resp = self.check_online(request, client_socket, con, cur)
                elif request['action'] == 'authorize':
                    resp = self.authorization(request, client_socket, con, cur)
                elif request['action'] == 'register':
                    resp = self.registration(request, con, cur)
                elif request['action'] == 'sign_out':
                    resp = self.sign_out(request, client_socket, con, cur)
                elif request['action'] == 'add_contact':
                    resp = self.add_contact(request, client_socket, con, cur)
                elif request['action'] == 'del_contact':
                    resp = self.del_contact(request, client_socket, con, cur)
                elif request['action'] == 'get_contacts':
                    resp = self.get_contacts(request, client_socket, con, cur)
                elif request['action'] == 'send_message':
                    resp = self.handle_message(request, client_socket, con, cur)
                else:
                    raise RuntimeError(f'Неизвестный запрос: {request["action"]}')
                client_socket.send(coder.encrypt(bytes(json.dumps(resp), encoding='utf8')))
            except Exception as e:
                print(e)
                client_socket.close()
                self.clients.remove(client_socket)
                try:
                    del self.logins[client_socket]
                except Exception:
                    pass
                break

    def check_online(self, request, client_socket, con, cur):
        """Проверяет, подключен ли пользователь к серверу"""
        resp = {'action': 'response', 'response': 200, 'error': None, 'online': None}
        client_login = request['user']['account_name']
        contact_login = request['user_id']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif contact_login in self.logins.values():
            resp['online'] = True
        elif contact_login not in self.logins.values():
            resp['online'] = False
        return resp

    def authorization(self, request, client_socket, con, cur):
        """Авторизация зарегистрированного пользователя"""
        resp = {'action': 'response', 'response': 200, 'error': None}
        client_login = request['user']['account_name']
        client_digest = request['user']['password']
        if not self.check_existence(client_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {client_login}'
        else:
            client_hash = self.get_password(client_login, con, cur)
            if not pwd_context.verify(client_digest, client_hash):
                resp['response'] = 403
                resp['error'] = 'Access denied'
            else:
                self.logins[client_socket] = client_login
        return resp

    def registration(self, request, con, cur):
        """Регистрация нового пользователя"""
        resp = {'action': 'response', 'response': 200, 'error': None}
        client_login = request['user']['account_name']
        client_digest = request['user']['password']
        if self.check_existence(client_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'Login is already taken: {client_login}'
        else:
            self.register(client_login, pwd_context.hash(client_digest), con, cur)
        return resp

    def sign_out(self, request, client_socket, con, cur):
        """Производит выход пользователя из сети"""
        resp = {'action': 'response', 'response': 200, 'error': None}
        client_login = request['user']['account_name']
        if not self.check_existence(client_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {client_login}'
        elif not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif client_login in self.logins.values():
            del self.logins[client_socket]
        elif client_login not in self.logins.values():
            resp['response'] = 400
            resp['error'] = f'{client_login} is offline'
        return resp

    def add_contact(self, request, client_socket, con, cur):
        """Добавление клиента в контакты авторизованного пользователя"""
        resp = {'action': 'response', 'response': 200, 'error': None}
        client_login = request['user']['account_name']
        contact_login = request['user_id']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif self.in_contacts(client_login, contact_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'Client already in contacts: {contact_login}'
        else:
            self.add_to_contacts(client_login, contact_login, con, cur)
        return resp

    def del_contact(self, request, client_socket, con, cur):
        """Удаление клиента из контактов авторизованного пользователя"""
        resp = {'action': 'response', 'response': 200, 'error': None}
        client_login = request['user']['account_name']
        contact_login = request['user_id']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif not self.in_contacts(client_login, contact_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'Client not in contacts: {contact_login}'
        else:
            self.del_from_contacts(client_login, contact_login, con, cur)
        return resp

    def get_contacts(self, request, client_socket, con, cur):
        """Возвращает список всех контактов авторизованного пользователя"""
        resp = {'action': 'response', 'response': 200, 'error': None, 'contacts': []}
        client_login = request['user']['account_name']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(client_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {client_login}'
        else:
            client_contacts = json.loads(self.get_client_contacts(client_login, con, cur))
            resp['contacts'] = client_contacts
        return resp

    def handle_message(self, request, client_socket, con, cur):
        """Обработка сообщения от одного пользователя другому"""
        resp = {'action': 'response', 'response': 200, 'error': None}
        client_login = request['user']['account_name']
        contact_login = request['to']
        message = {'action': 'message', 'from': client_login, 'message': None}
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login, con, cur):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif contact_login in self.logins.values():
            message['message'] = request['message']
            for socket, login in self.logins.items():
                if login == contact_login:
                    socket.send(self.coders[socket].encrypt(bytes(json.dumps(message), encoding='utf8')))
                    break
        elif contact_login not in self.logins.values():
            resp['response'] = 400
            resp['error'] = f'{contact_login} is offline'
        return resp

    def register(self, client_login, client_password, con, cur):
        """Регистрация нового пользователя в базе данных"""
        cur.execute("""INSERT INTO users(login, password, contacts) 
                    VALUES(?, ?, '[]')""", (client_login, client_password))
        con.commit()

    def check_authorization(self, client_socket, client_login):
        """Проверяет, авторизован ли пользователь"""
        if client_socket not in self.logins.keys():
            return False
        return self.logins[client_socket] == client_login

    def check_existence(self, client_login, con, cur):
        """Проверяет, существует ли пользователь в базе данных"""
        return bool(cur.execute("""SELECT login FROM users
                    WHERE login = ?""", (client_login,)).fetchall())

    def get_password(self, client_login, con, cur):
        """Получает сохраненный в базе данных пароль пользователя"""
        return cur.execute("""SELECT password FROM users
                    WHERE login = ?""", (client_login,)).fetchone()[0]

    def in_contacts(self, client_login, contact_login, con, cur):
        """Проверяет, есть ли пользователь в контактах"""
        contacts = json.loads(cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone()[0])
        return contact_login in contacts

    def add_to_contacts(self, client_login, contact_login, con, cur):
        """Добавляет пользователя в контакты"""
        contacts = json.loads(cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone()[0])
        contacts.append(contact_login)
        cur.execute("""UPDATE users
                    SET contacts = ?
                    WHERE login = ?""", (json.dumps(contacts), client_login))
        con.commit()

    def del_from_contacts(self, client_login, contact_login, con, cur):
        """Удаляет пользователя из контактов"""
        contacts = json.loads(cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone()[0])
        del contacts[contacts.index(contact_login)]
        cur.execute("""UPDATE users
                    SET contacts = ?
                    WHERE login = ?""", (json.dumps(contacts), client_login))
        con.commit()

    def get_client_contacts(self, client_login, con, cur):
        """Получает список контактов пользователя из базы данных"""
        return cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone()[0]


if __name__ == '__main__':
    server = Server()
    server.start()
