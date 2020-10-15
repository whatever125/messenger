import sys
import socket

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('messenger.ui', self)
        self.ip = ''
        self.pushButton.clicked.connect(self.connect)
        self.pushButton_2.clicked.connect(self.send)
        self.pushButton_3.clicked.connect(self.check)

    def send(self):
        try:
            assert self.ip
        except AssertionError:
            print('Not connected to the server')
        else:
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            self.client_sock.connect((self.ip, 55321))
            self.client_sock.sendall(bytes(self.textEdit.toPlainText(), encoding='utf-8'))
            self.textEdit_2.append(f'<Вы>: {self.textEdit.toPlainText()}')
            message = self.client_sock.recv(1024)
            if message:
                self.textEdit_2.append(f'<Собеседник>: {str(message, encoding="utf-8")}')
            self.client_sock.close()


    def connect(self):
        try:
            self.ip = self.lineEdit.text()
            assert self.ip
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            self.client_sock.connect((self.ip, 55321))
            self.client_sock.close()
            print('Successfully connected')
        except Exception:
            print('Error while connecting')
            self.ip = ''
        

    def check(self):
        message = self.client_sock.recv(1024)
        if message:
            self.textEdit_2.append(f'<Собеседник>: {str(message, encoding="utf-8")}')
        self.client_sock.close()




if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())
