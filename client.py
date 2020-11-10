import sys
import socket
import json
import threading

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog, QWidget, QTextEdit
from PyQt5.QtCore import QMargins, Qt, QTimer

class LTextEdit(QTextEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() != Qt.ShiftModifier:
            self.send()
        else:
            QTextEdit.keyPressEvent(self, event)

class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('reg.ui', self)
        x, y = self.size().width() // 4, self.size().height() // 4
        self.gridLayout.setContentsMargins(QMargins(x, y, x, y))
        self.bull = True
        self.response = None
        widget = QWidget(self)
        widget.setLayout(self.gridLayout)
        self.setCentralWidget(widget)
        self.ip = 'localhost'
        self.pushButton.clicked.connect(self.auth)
        self.pushButton_2.clicked.connect(self.reg)

    def threading_function(self):
        while True:
            try:
                self.response = self.client_sock.recv(1024)
                print(json.loads(self.response))
                data = self.response
                if 'action' in json.loads(data).keys():
                    data = json.loads(data)
                    chat = open(f'messages/{self.login};{data["from"]}', 'a')
                    chat.write(f'<font color = #50c878>{data["from"]}: <\\font>\n')
                    new_text = data['message'].split('\n')
                    for i in new_text:
                        chat.write(f'<font color = #ffffff>{i}<\\font>\n')
                    chat.close()
                    self.openchat()
            except Exception as E:
                return None

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
        self.bull = False
        widget = QWidget(self)
        widget.setLayout(self.gridLayout)
        self.setCentralWidget(widget)
        self.t = threading.Thread(target=self.threading_function)
        self.t.start()
        self.label.setText(self.login)
        self.pushButton.clicked.connect(self.send)
        self.pushButton_5.clicked.connect(self.logout)
        self.pushButton_2.clicked.connect(self.addcontact)
        self.pushButton_3.clicked.connect(self.delcontact)
        self.listWidget.itemSelectionChanged.connect(self.openchat)
        contacts = self.getcontacts()['contacts']
        for i in contacts:
            self.listWidget.addItem(i)
        self.getmessages()

    def logout(self):
        self.client_sock.close()
        uic.loadUi('reg.ui', self)
        widget = QWidget(self)
        widget.setLayout(self.gridLayout)
        self.setCentralWidget(widget)
        x, y = self.size().width() // 4, self.size().height() // 4
        self.gridLayout.setContentsMargins(QMargins(x, y, x, y))
        self.bull = True
        self.ip = 'localhost'
        self.pushButton.clicked.connect(self.auth)
        self.pushButton_2.clicked.connect(self.reg)

    def getcontacts(self):
        try:
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'get_contacts', 'user': {'account_name': self.login}}),
                encoding='utf8'))
            self.t.join(0.05)
            data = self.response
            return json.loads(data)
        except Exception as E:
            print(E)

    def addcontact(self):
        try:
            name, ok_pressed = QInputDialog.getText(self, "Введите имя контакта",
                                                    "Добавить новый контакт:")
            if ok_pressed:
                chat = open(f'messages/{self.login};{name}', 'a')
                chat.close()
                self.client_sock.sendall(bytes(
                    json.dumps(
                        {'action': 'add_contact', 'user': {'account_name': self.login},
                         'user_id': name}),
                    encoding='utf8'))
                self.t.join(0.05)
                data = json.loads(self.response)
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
            self.t.join(0.05)
            data = json.loads(self.response)
            if data['response'] == 200:
                self.listWidget.clear()
                contacts = self.getcontacts()['contacts']
                for i in contacts:
                    self.listWidget.addItem(i)
            print(data)
        except Exception as E:
            print(E)

    def addmessage(self, sender, text):
        new_text = text.split('\n')
        self.textEdit.append(f'<font color = #50c878>{sender}: <\\font>')
        for i in new_text:
            self.textEdit.append(f'<font color = #ffffff>{i}<\\font>')
        chat = open(f'messages/{self.login};{self.label_2.text()}', 'a')
        chat.write(f'<font color = #50c878>{sender}: <\\font>\n')
        for i in new_text:
            chat.write(f'<font color = #ffffff>{i}<\\font>\n')

    def getmessages(self):
        try:
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'get_messages', 'user': {'account_name': self.login}}),
                encoding='utf8'))
            self.t.join(0.05)
            data = self.response
            print(json.loads(data)['messages'])
            for i in json.loads(data)['messages']:
                chat = open(f'messages/{self.login};{i["from"]}', 'a')
                chat.write(f'<font color = #50c878>{i["from"]}: <\\font>\n')
                new_text = i['message'].split('\n')
                for i in new_text:
                    chat.write(f'<font color = #ffffff>{i}<\\font>\n')
                chat.close()
        except Exception as E:
            print(E)

    def send(self):
        try:
            if not self.label_2.text() or not self.textEdit_2.toPlainText():
                return None
            self.client_sock.sendall(bytes(
                json.dumps(
                    {'action': 'send_message', 'user': {'account_name': self.login},
                     'to': self.label_2.text(), 'message': self.textEdit_2.toPlainText()}),
                encoding='utf8'))
            self.t.join(0.1)
            data = self.response
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

    def resizeEvent(self, event):
        QMainWindow.resizeEvent(self, event)
        if self.bull:
            x, y = self.size().width() // 4, self.size().height() // 4
            self.gridLayout.setContentsMargins(QMargins(x, y, x, y))

    def keyPressEvent(self, event):
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