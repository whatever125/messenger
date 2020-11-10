import sys
import socket
import json
import threading

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog, QWidget, QTextEdit, \
    QColorDialog
from PyQt5.QtCore import QMargins, Qt, pyqtSignal, QObject


class LTextEdit(QTextEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() != Qt.ShiftModifier:
            self.send()
        else:
            QTextEdit.keyPressEvent(self, event)


class SettingsDialog(QWidget):
    def __init__(self, main):
        super().__init__()
        uic.loadUi('dialog.ui', self)
        self.main = main
        self.pushButton.clicked.connect(main.changecolor1)
        self.pushButton_3.clicked.connect(main.changecolor2)
        self.pushButton_2.clicked.connect(main.default)

class Communicate(QObject):
    newMessage = pyqtSignal()


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('reg.ui', self)
        try:
            f = open('messages/settings', 'r').readlines()
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
            self.c.newMessage.connect(self.shownewmessages)
            widget = QWidget(self)
            widget.setLayout(self.gridLayout)
            self.setCentralWidget(widget)
            self.ip = 'localhost'
            self.pushButton.clicked.connect(self.auth)
            self.pushButton_2.clicked.connect(self.reg)
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
        while True:
            try:
                self.response = self.client_sock.recv(1024)
                self.responses.append(self.response)
                data = json.loads(self.response)
                if data['action'] == 'message':
                    self.c.newMessage.emit()
            except Exception:
                return None

    def shownewmessages(self):
        data = self.responses[-1]
        data = json.loads(data)
        chat = open(f'messages/{self.login};{data["from"]}', 'a')
        chat.write(f'<font color = #50c878>{data["from"]}: <\\font>\n')
        new_text = data['message'].split('\n')
        for i in new_text:
            chat.write(f'<font color = #ffffff>{i}<\\font>\n')
        chat.close()
        self.openchat()


    def auth(self):
        try:
            login = self.lineEdit.text()
            password = self.lineEdit_2.text()
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_sock.connect((self.ip, 54322))
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
        self.responses = []
        self.recolor()
        self.label.setText(self.login)
        self.pushButton.clicked.connect(self.send)
        self.pushButton_5.clicked.connect(self.logout)
        self.pushButton_2.clicked.connect(self.addcontact)
        self.pushButton_3.clicked.connect(self.delcontact)
        self.pushButton_4.clicked.connect(self.settings)
        self.listWidget.itemSelectionChanged.connect(self.openchat)
        contacts = self.getcontacts()['contacts']
        for i in contacts:
            self.listWidget.addItem(i)
        self.getmessages()

    def logout(self):
        self.client_sock.close()
        uic.loadUi('reg.ui', self)
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
        self.textEdit.append(f'<font color = {self.color1}>{sender}: <\\font>')
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
                for j in new_text:
                    chat.write(f'<font color = #ffffff>{j}<\\font>\n')
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
                i = i.replace('#50c878', self.color1)
                self.textEdit.append(i)
        except Exception as E:
            print(E)

    def changecolor1(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color1 = color.name()
        f = open('messages/settings', 'w')
        f.writelines(f'{self.color1}\n{self.color2}')
        f.close()
        self.recolor()

    def changecolor2(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color2 = color.name()
        f = open('messages/settings', 'w')
        f.write(f'{self.color1}\n{self.color2}')
        f.close()
        self.recolor()

    def default(self):
        self.color1 = '#50c878'
        self.color2 = '#ffffff'
        f = open('messages/settings', 'w')
        f.write('#50c878\n#ffffff')
        f.close()
        self.recolor()

    def recolor(self):
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
        self.second_form = SettingsDialog(self)
        self.second_form.show()

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