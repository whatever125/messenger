import sys
import socket
import json
import zlib
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog
from PyQt5.QtWidgets import QWidget, QTextEdit, QColorDialog
from PyQt5.QtCore import QMargins, Qt, pyqtSignal, QObject
# from interface import *
from PyQt5 import uic

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet


def read_public(key):
    public_key = serialization.load_pem_public_key(
        key,
        backend=default_backend()
    )
    return public_key


def encrypt(data, key):
    public_key = read_public(key)
    encrypted = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted


class SettingsDialog(QWidget):
    """Класс окна настроек, изменяющий два основных цвета дизайна приложения"""
    def __init__(self, main):
        super().__init__()
        # self.setupUi(self)
        uic.loadUi('dialog.ui', self)
        try:
            f = open('settings', 'r').readlines()
            self.color1 = f[0]
            self.color2 = f[1]
        except Exception:
            self.color1 = '#50c878'
            self.color2 = '#ffffff'
        finally:
            self.recolor()
        self.main = main
        self.pushButton.clicked.connect(main.change_color1)
        self.pushButton.clicked.connect(self.change_color1)
        self.pushButton_2.clicked.connect(main.default)
        self.pushButton_2.clicked.connect(self.default)
        self.pushButton_3.clicked.connect(main.change_color2)
        self.pushButton_3.clicked.connect(self.change_color2)

    def change_color1(self):
        """Меняет основной цвет приложения на выбранный пользователем"""
        self.color1 = self.main.color1
        self.recolor()

    def change_color2(self):
        """Меняет дополнительный цвет приложения на выбранный пользователем"""
        self.color2 = self.main.color2
        self.recolor()

    def recolor(self):
        """Изменяет цвета основого окна приложения"""
        self.label.setStyleSheet(f'color:{self.color1};')
        buttons = [self.pushButton, self.pushButton_2, self.pushButton_3]
        for i in buttons:
            i.setStyleSheet(f"    background-color:{self.color1};\n"
                            "     border-style: outset;\n"
                            "     border-width: 2px;\n"
                            "     border-radius: 10px;\n"
                            "     border-color: beige;\n"
                            "     padding: 6px;\n"
                            f"color: {self.color2};")

    def default(self):
        """Возвращает цветовые настройки в исходное состояние"""
        self.color1 = '#50c878'
        self.color2 = '#ffffff'
        self.recolor()


class Communicate(QObject):
    """Класс объекта, отправляющий сигналы в приложение при получении новых сообщений"""
    newMessage = pyqtSignal()


class MyWidget(QMainWindow):
    """Класс основного окна мессенджера"""
    def __init__(self):
        """Инициализация класса"""
        super().__init__()
        # self.setupRegUi(self)
        uic.loadUi('reg.ui', self)
        try:
            f = open('settings', 'r').readlines()
            self.color1 = f[0]
            self.color2 = f[1]
        except Exception:
            self.color1 = '#50c878'
            self.color2 = '#ffffff'
        finally:
            x, y = self.size().width() // 4, self.size().height() // 4
            self.gridLayout.setContentsMargins(QMargins(x, y, x, y))
            self.bull = True
            self.response = None
            self.c = Communicate()
            self.c.newMessage.connect(self.show_messages)
            widget = QWidget(self)
            widget.setLayout(self.gridLayout)
            self.setCentralWidget(widget)
            self.ip = 'localhost'
            self.coder = None
            self.pushButton.clicked.connect(self.authorize)
            self.pushButton_2.clicked.connect(self.register)
            labels = [self.label, self.label_2, self.label_3, self.label_4]
            buttons = [self.pushButton, self.pushButton_2]
            for i in labels:
                i.setStyleSheet(f'color:{self.color1};')
            for i in buttons:
                i.setStyleSheet(f"    background-color:{self.color1};\n"
                                "     border-style: outset;\n"
                                "     border-width: 2px;\n"
                                "     border-radius: 10px;\n"
                                "     border-color: beige;\n"
                                "     padding: 6px;\n"
                                f"color: {self.color2};")

    def threading_function(self):
        """Поток,получающий все данные от сервера"""
        while True:
            try:
                self.response = self.coder.decrypt(zlib.decompress(self.client_socket.recv(1024)))
                self.responses.append(self.response)
                data = json.loads(self.response)
                if data['action'] == 'message':
                    self.c.newMessage.emit()
            except Exception:
                return None

    def show_messages(self):
        """Обрабатывает полученные сообщения"""
        data = self.responses[-1]
        data = json.loads(data)
        chat = open(f'messages/{self.login};{data["from"]}', 'a')
        chat.write(f'<font color = #50c878>{data["from"]}: <\\font>\n')
        new_text = data['message'].split('\n')
        for i in new_text:
            chat.write(f'<font color = #ffffff>{i}<\\font>\n')
        chat.close()
        self.open_chat()

    def authorize(self):
        """Отправляет на сервер запрос авторизации"""
        try:
            login = self.lineEdit.text()
            password = self.lineEdit_2.text()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, 54321))

            self.set_keys()

            self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                json.dumps(
                    {"action": "authorize", 'user': {'account_name': login, 'password': password}}),
                encoding='utf8'))))
            data = json.loads(self.coder.decrypt(zlib.decompress(self.client_socket.recv(1024))))
            self.error.setText(data['error'])
            if data['response'] == 200:
                self.login = login
                self.messenger()
        except Exception as E:
            print(E)

    def register(self):
        """Отправляет на сервер запрос регистрации, после чего вызывает функцию авторизации"""
        try:
            login = self.lineEdit.text()
            password = self.lineEdit_2.text()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, 54321))

            self.set_keys()

            self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                json.dumps(
                    {'action': 'register', 'user': {'account_name': login, 'password': password}}),
                encoding='utf8'))))
            data = json.loads(self.coder.decrypt(zlib.decompress(self.client_socket.recv(1024))))
            self.error.setText(data['error'])
            self.client_socket.close()
            if data['response'] == 200:
                self.authorize()
        except Exception as E:
            print(E)

    def set_keys(self):
        public_key = zlib.decompress(self.client_socket.recv(1024))
        key = Fernet.generate_key()
        self.coder = Fernet(key)
        key_data = encrypt(key, public_key)
        self.client_socket.sendall(zlib.compress(key_data))

    def messenger(self):
        """Выводит основное окно приложения после успешной авторизации"""
        # self.setupUi(self)
        uic.loadUi('messenger.ui', self)
        self.bull = False
        widget = QWidget(self)
        widget.setLayout(self.gridLayout)
        self.setCentralWidget(widget)
        self.t = threading.Thread(target=self.threading_function, daemon=True)
        self.t.start()
        self.responses = []
        self.recolor()
        self.label.setText(self.login)
        self.pushButton.clicked.connect(self.send)
        self.pushButton_5.clicked.connect(self.logout)
        self.pushButton_2.clicked.connect(self.add_contact)
        self.pushButton_3.clicked.connect(self.del_contact)
        self.pushButton_4.clicked.connect(self.settings)
        self.listWidget.itemSelectionChanged.connect(self.open_chat)
        contacts = self.get_contacts()['contacts']
        for i in contacts:
            self.listWidget.addItem(i)

    def logout(self):
        """Возвращает пользователя в меню регистрации/входа после выхода из аккаунта"""
        try:
            self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                json.dumps(
                    {'action': 'sign_out', 'user': {'account_name': self.login}}),
                encoding='utf8'))))
            self.t.join(0.05)
            data = json.loads(self.response)
        except Exception as E:
            print(E)
        self.client_socket.close()
        # self.setupRegUi(self)
        uic.loadUi('reg.ui', self)
        self.recolor()
        widget = QWidget(self)
        widget.setLayout(self.gridLayout)
        self.setCentralWidget(widget)
        x, y = self.size().width() // 4, self.size().height() // 4
        self.gridLayout.setContentsMargins(QMargins(x, y, x, y))
        self.bull = True
        self.ip = 'localhost'
        self.pushButton.clicked.connect(self.authorize)
        self.pushButton_2.clicked.connect(self.register)

    def get_contacts(self):
        """Получает от сервера контакты пользователя"""
        try:
            self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                json.dumps(
                    {'action': 'get_contacts', 'user': {'account_name': self.login}}),
                encoding='utf8'))))
            self.t.join(0.05)
            data = json.loads(self.response)
            return data
        except Exception as E:
            print(E)

    def add_contact(self):
        """Добавляет нового пользователя в список контактов"""
        try:
            name, ok_pressed = QInputDialog.getText(self, "Введите имя контакта",
                                                    "Добавить новый контакт:")
            if ok_pressed:
                self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                    json.dumps(
                        {'action': 'add_contact', 'user': {'account_name': self.login},
                         'user_id': name}),
                    encoding='utf8'))))
                self.t.join(0.05)
                data = json.loads(self.response)
                if data['response'] == 200:
                    chat = open(f'messages/{self.login};{name}', 'w')
                    chat.close()
                    self.listWidget.addItem(name)
        except Exception as E:
            print(E)

    def del_contact(self):
        """Удаляет выбранного пользователя из списка контактов"""
        try:
            name = self.listWidget.selectedItems()[0].text()
            self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                json.dumps(
                    {'action': 'del_contact', 'user': {'account_name': self.login},
                     'user_id': name}),
                encoding='utf8'))))
            self.t.join(0.05)
            data = json.loads(self.response)
            if data['response'] == 200:
                self.listWidget.clear()
                contacts = self.get_contacts()['contacts']
                for i in contacts:
                    self.listWidget.addItem(i)
        except Exception as E:
            print(E)

    def add_message(self, sender, text):
        """Выводит на экран сообщение, принимая в качестве аргументов имя отправителя и текст"""
        new_text = text.split('\n')
        self.textEdit.append(f'<font color = {self.color1}>{sender}: <\\font>')
        for i in new_text:
            self.textEdit.append(f'<font color = #ffffff>{i}<\\font>')
        chat = open(f'messages/{self.login};{self.label_2.text()}', 'a')
        chat.write(f'<font color = #50c878>{sender}: <\\font>\n')
        for i in new_text:
            chat.write(f'<font color = #ffffff>{i}<\\font>\n')

    def send(self):
        """Отправляет сообщение пользователю"""
        try:
            if not self.label_2.text() or not self.textEdit_2.toPlainText():
                return None
            self.client_socket.sendall(zlib.compress(self.coder.encrypt(bytes(
                json.dumps(
                    {'action': 'send_message', 'user': {'account_name': self.login},
                     'to': self.label_2.text(), 'message': self.textEdit_2.toPlainText()}),
                encoding='utf8'))))
            self.t.join(0.1)
            data = json.loads(self.response)
            if data['response'] == 200:
                self.add_message(self.login, self.textEdit_2.toPlainText())
                self.textEdit_2.clear()
        except Exception as E:
            print(E)

    def open_chat(self):
        """Открывает диалог с выбранным пользователем"""
        if len(self.listWidget.selectedItems()) == 0:
            return None
        self.textEdit.clear()
        name = self.listWidget.selectedItems()[0].text()
        chat = open(f'messages/{self.login};{name}', 'a')
        chat.close()
        self.label_2.setText(name)
        try:
            chat = open(f'messages/{self.login};{name}', 'r').readlines()
            for i in chat:
                i = i.replace('#50c878', self.color1)
                self.textEdit.append(i)
        except Exception as E:
            print(E)

    def change_color1(self):
        """Меняет основной цвет приложения на выбранный пользователем"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.color1 = color.name()
        f = open('settings', 'w')
        f.writelines(f'{self.color1}\n{self.color2}')
        f.close()
        self.recolor()

    def change_color2(self):
        """Меняет дополнительный цвет приложения на выбранный пользователем"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.color2 = color.name()
        f = open('settings', 'w')
        f.write(f'{self.color1}\n{self.color2}')
        f.close()
        self.recolor()

    def default(self):
        """Возвращает цветовые настройки в исходное состояние"""
        self.color1 = '#50c878'
        self.color2 = '#ffffff'
        f = open('settings', 'w')
        f.write('#50c878\n#ffffff')
        f.close()
        self.recolor()

    def recolor(self):
        """Изменяет цвета основого окна приложения"""
        labels = [self.label, self.label_2]
        buttons = [self.pushButton, self.pushButton_2, self.pushButton_3, self.pushButton_4,
                   self.pushButton_5]
        for i in labels:
            i.setStyleSheet(f'color:{self.color1};')
        for i in buttons:
            i.setStyleSheet(f"    background-color:{self.color1};\n"
                            "     border-style: outset;\n"
                            "     border-width: 2px;\n"
                            "     border-radius: 10px;\n"
                            "     border-color: beige;\n"
                            "     padding: 6px;\n"
                            f"color: {self.color2};")

    def settings(self):
        """Открывает меню настроек"""
        self.second_form = SettingsDialog(self)
        self.second_form.show()

    def resizeEvent(self, event):
        """Создаёт отступы от краёв окна входа/регистрации в размере четверти от его длины и
        ширины"""
        QMainWindow.resizeEvent(self, event)
        if self.bull:
            x, y = self.size().width() // 4, self.size().height() // 4
            self.gridLayout.setContentsMargins(QMargins(x, y, x, y))

    def keyPressEvent(self, event):
        """Отправляет введённое сообщение при нажатии на Enter"""
        try:
            if event.key() == Qt.Key_Return:
                self.send()
        except Exception as E:
            print(E)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())
