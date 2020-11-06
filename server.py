import json
import sqlite3
import socket
import threading


class Server:
    def __init__(self):
        self.host = 'localhost'
        self.port = 54321
        self.socket = None
        self.clients = []
        self.logins = {}

    def start(self):
        if self.socket:
            raise RuntimeError('Already started')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1024)
        self.socket.settimeout(100000000)
        while True:
            client_socket, address = self.socket.accept()
            t = threading.Thread(target=self.mainloop, args=(client_socket, address))
            t.start()

    def mainloop(self, client_socket, address):
        print(f'Client connected: {address}')
        print()
        self.con = sqlite3.connect("messenger.sql")
        self.cur = self.con.cursor()
        self.clients.append(client_socket)
        while True:
            try:
                request = json.loads(client_socket.recv(1024))
                print(f'Request from {address}:')
                print(request)
                if request['action'] == 'check_online':
                    resp = self.check_online(request, client_socket)
                elif request['action'] == 'authorize':
                    resp = self.authorization(request, client_socket)
                elif request['action'] == 'register':
                    resp = self.registration(request)
                elif request['action'] == 'add_contact':
                    resp = self.add_contact(request, client_socket)
                elif request['action'] == 'del_contact':
                    resp = self.del_contact(request, client_socket)
                elif request['action'] == 'get_contacts':
                    resp = self.get_contacts(request, client_socket)
                elif request['action'] == 'send_message':
                    resp = self.handle_message(request, client_socket)
                elif request['action'] == 'get_messages':
                    resp = self.get_messages(request, client_socket)
                else:
                    raise RuntimeError(f'Unknown request: {request["action"]}')
                print(f'Response to {address}:')
                print(resp)
                print()
                client_socket.send(bytes(json.dumps(resp), encoding='utf8'))
            except Exception as e:
                print(f'Client disconnected: {address}')
                print()
                client_socket.close()
                self.clients.remove(client_socket)
                try:
                    del self.logins[client_socket]
                except Exception:
                    pass
                break

    def check_online(self, request, client_socket):
        resp = {'response': 200, 'error': None, 'online': None}
        client_login = request['user']['account_name']
        contact_login = request['user_id']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif contact_login in self.logins.values():
            resp['online'] = True
        elif contact_login not in self.logins.values():
            resp['online'] = False
        return resp

    def authorization(self, request, client_socket):
        resp = {'response': 200, 'error': None}
        client_login = request['user']['account_name']
        client_digest = request['user']['password']
        if not self.check_existence(client_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {client_login}'
        elif client_login in self.logins.values():
            resp['response'] = 403
            resp['error'] = 'Access denied'
        else:
            client_hash = self.get_password(client_login)
            if client_hash != client_digest:
                resp['response'] = 403
                resp['error'] = 'Access denied'
            else:
                self.logins[client_socket] = client_login
        return resp

    def registration(self, request):
        resp = {'response': 200, 'error': None}
        client_login = request['user']['account_name']
        client_digest = request['user']['password']
        if self.check_existence(client_login):
            resp['response'] = 400
            resp['error'] = f'Login is already taken: {client_login}'
        else:
            self.register(client_login, client_digest)
        return resp

    def add_contact(self, request, client_socket):
        resp = {'response': 200, 'error': None}
        client_login = request['user']['account_name']
        contact_login = request['user_id']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif self.in_contacts(client_login, contact_login):
            resp['response'] = 400
            resp['error'] = f'Client already in contacts: {contact_login}'
        else:
            self.add_to_contacts(client_login, contact_login)
        return resp

    def del_contact(self, request, client_socket):
        resp = {'response': 200, 'error': None}
        client_login = request['user']['account_name']
        contact_login = request['user_id']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif not self.in_contacts(client_login, contact_login):
            resp['response'] = 400
            resp['error'] = f'Client not in contacts: {contact_login}'
        else:
            self.del_from_contacts(client_login, contact_login)
        return resp

    def get_contacts(self, request, client_socket):
        resp = {'response': 200, 'error': None, 'contacts': []}
        client_login = request['user']['account_name']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(client_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {client_login}'
        else:
            client_contacts = json.loads(self.get_client_contacts(client_login))
            resp['contacts'] = client_contacts
        return resp

    def handle_message(self, request, client_socket):
        resp = {'response': 200, 'error': None}
        client_login = request['user']['account_name']
        contact_login = request['to']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(contact_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {contact_login}'
        elif contact_login in self.logins.values():
            message = json.dumps(request)
            for socket, login in self.logins.items():
                if login == contact_login:
                    socket.send(bytes(json.dumps(message), encoding='utf8'))
                    break
        elif contact_login not in self.logins.values():
            self.add_unread_messages(contact_login, request)
        return resp

    def get_messages(self, request, client_socket):
        resp = {'response': 200, 'error': None, 'messages': []}
        client_login = request['user']['account_name']
        if not self.check_authorization(client_socket, client_login):
            resp['response'] = 403
            resp['error'] = 'Access denied'
        elif not self.check_existence(client_login):
            resp['response'] = 400
            resp['error'] = f'No such client: {client_login}'
        else:
            client_contacts = json.loads(self.get_unread_messages(client_login))
            resp['messages'] = client_contacts
        return resp

    def register(self, client_login, client_password):
        self.cur.execute("""INSERT INTO users(login, password, contacts) 
                    VALUES(?, ?, '[]')""", (client_login, client_password))
        self.con.commit()

    def check_authorization(self, client_socket, client_login):
        if client_socket not in self.logins.keys():
            return False
        return self.logins[client_socket] == client_login

    def check_existence(self, client_login):
        return bool(self.cur.execute("""SELECT login FROM users
                    WHERE login = ?""", (client_login,)).fetchall())

    def get_password(self, client_login):
        return self.cur.execute("""SELECT password FROM users
                    WHERE login = ?""", (client_login,)).fetchone()

    def in_contacts(self, client_login, contact_login):
        contacts = json.loads(self.cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone())
        return contact_login in contacts

    def add_to_contacts(self, client_login, contact_login):
        contacts = json.loads(self.cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone())
        contacts.append(contact_login)
        self.cur.execute("""UPDATE users
                    SET contacts = ?
                    WHERE login = ?""", (json.dumps(contacts), client_login))
        self.con.commit()

    def del_from_contacts(self, client_login, contact_login):
        contacts = json.loads(self.cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone())
        del contacts[contacts.index(contact_login)]
        self.cur.execute("""UPDATE users
                    SET contacts = ?
                    WHERE login = ?""", (json.dumps(contacts), client_login))
        self.con.commit()

    def get_client_contacts(self, client_login):
        return self.cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone()

    def add_unread_messages(self, client_login, message):
        messages = json.loads(self.cur.execute("""SELECT contacts FROM users
                    WHERE login = ?""", (client_login,)).fetchone())
        messages.append(message)
        self.cur.execute("""UPDATE users
                    SET messages = ?
                    WHERE login = ?""", (json.dumps(messages), client_login))
        self.con.commit()

    def get_unread_messages(self, client_login):
        messages =  self.cur.execute("""SELECT contacts FROM users
                            WHERE login = ?""", (client_login,)).fetchone()
        self.cur.execute("""UPDATE users
                    SET messages = []
                    WHERE login = ?""", (client_login,))
        self.con.commit()
        return messages


if __name__ == '__main__':
    server = Server()
    server.start()
