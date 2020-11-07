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
        self.pushButton.clicked.connect(self.send)
        self.pushButton_5.clicked.connect(self.logout)
        self.pushButton_2.clicked.connect(self.addcontact)
        self.pushButton_3.clicked.connect(self.delcontact)
        self.listWidget.itemSelectionChanged.connect(self.openchat)
        print(self.getcontacts())
        contacts = self.getcontacts()['contacts']
        for i in contacts:
            self.listWidget.addItem(i)
        self.getmessages()

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
                chat = open(f'messages/{self.login};{name}', 'w')
                chat.close()
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
            name = self.listWidget.selectedItems()[0].text()
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'del_contact', 'user': {'account_name': self.login},
                     'user_id': name}),
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

    def addmessage(self, sender, text):
        self.textEdit.append(f'<font color = #50c878>{sender}: <\\font>')
        self.textEdit.append(f'<font color = #ffffff>{text}<\\font>')
        chat = open(f'messages/{self.login};{self.label_2.text()}', 'a')
        chat.write(f'<font color = #50c878>{sender}: <\\font>\n')
        chat.write(f'<font color = #ffffff>{text}<\\font>\n')
        self.textEdit.append('')

    def getmessages(self):
        try:
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'get_messages', 'user': {'account_name': self.login}}),
                encoding='utf8'))
            data = self.client_sock.recv(1024)
            print(json.loads(data)['messages'])
            for i in json.loads(data)['messages']:
                chat = open(f'messages/{self.login};{i["from"]}', 'a')
                chat.write(f'<font color = #50c878>{i["from"]}: <\\font>\n')
                chat.write(f'<font color = #ffffff>{i["message"]}<\\font>\n')
                chat.close()
        except Exception as E:
            print(E)

    def send(self):
        try:
            if not self.label_2.text():
                return None
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'send_message', 'user': {'account_name': self.login},
                     'to': self.label_2.text(), 'message': self.textEdit_2.toPlainText()}),
                encoding='utf8'))
            data = self.client_sock.recv(1024)
            print(json.loads(data))
            if json.loads(data)['response'] == 200:
                self.addmessage(self.login, self.textEdit_2.toPlainText())
                self.textEdit_2.clear()
        except Exception as E:
            print(E)

    def openchat(self):
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
                self.textEdit.append(i)
        except Exception as E:
            print(E)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())
