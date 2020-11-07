import sys
import socket
import json

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('reg.ui', self)
        self.ip = 'localhost'
        self.pushButton.clicked.connect(self.auth)
        self.pushButton_2.clicked.connect(self.reg)

    def auth(self):
        try:
            login = self.lineEdit.text()
            password = self.lineEdit_2.text()
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_sock.connect((self.ip, 54321))
            self.client_sock.sendall(bytes(
                json.dumps(
                    {"action": "authorize", 'user': {'account_name': login, 'password': password}}),
                encoding='utf8'))
            data = self.client_sock.recv(1024)
            self.error.setText(json.loads(data)['error'])
            print(json.loads(data))
            if json.loads(data)['response'] == 200:
                self.login = login
                self.password = password
                self.messenger()
            else:
                print('error')
        except Exception as E:
            print(E)

    def reg(self):
        try:
            login = self.lineEdit.text()
            password = self.lineEdit_2.text()
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_sock.connect((self.ip, 54321))
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'register', 'user': {'account_name': login, 'password': password}}),
                encoding='utf8'))
            data = self.client_sock.recv(1024)
            self.error.setText(json.loads(data)['error'])
            self.client_sock.close()
            if json.loads(data)['response'] == 200:
                self.auth()
        except Exception as E:
            print(E)

    def messenger(self):
        uic.loadUi('messenger.ui', self)
        self.label.setText(self.login)
        self.pushButton_5.clicked.connect(self.logout)
        self.pushButton_2.clicked.connect(self.addcontact)
        self.pushButton_3.clicked.connect(self.delcontact)
        print(self.getcontacts())
        contacts = self.getcontacts()['contacts']
        for i in contacts:
            self.listWidget.addItem(i)

    def logout(self):
        self.client_sock.close()
        uic.loadUi('reg.ui', self)
        self.ip = 'localhost'
        self.pushButton.clicked.connect(self.auth)
        self.pushButton_2.clicked.connect(self.reg)

    def getcontacts(self):
        try:
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'get_contacts', 'user': {'account_name': self.login}}),
                encoding='utf8'))
            data = self.client_sock.recv(1024)
            return json.loads(data)
        except Exception as E:
            print(E)

    def addcontact(self):
        try:
            name, ok_pressed = QInputDialog.getText(self, "Введите имя контакта",
                                                    "Добавить новый контакт:")
            if ok_pressed:
                self.client_sock.sendall(bytes(
                    json.dumps(
                        {'action': 'add_contact', 'user': {'account_name': self.login},
                         'user_id': name}),
                    encoding='utf8'))
                data = json.loads(self.client_sock.recv(1024))
                if data['response'] == 200:
                    self.listWidget.addItem(name)
                print(data)
        except Exception as E:
            print(E)

    def delcontact(self):
        try:
            name = self.listWidget.selectedItems()[0]
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'del_contact', 'user': {'account_name': self.login},
                     'user_id': name.text()}),
                encoding='utf8'))
            data = json.loads(self.client_sock.recv(1024))
            if data['response'] == 200:
                self.listWidget.clear()
                contacts = self.getcontacts()['contacts']
                for i in contacts:
                    self.listWidget.addItem(i)
            print(data)
        except Exception as E:
            print(E)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())