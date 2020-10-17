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

    def send(self):
        try:
            assert self.ip
        except AssertionError:
            print('Not connected to the server')
        else:
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            self.client_sock.connect((self.ip, 55321))
            send_data = self.textEdit.toPlainText()
            self.client_sock.sendall(send_data.encode('utf-8'))
            self.textEdit_2.append(f'<Вы>: {send_data}')
            message = self.client_sock.recv(1024)
            if message:
                self.textEdit_2.append(f'<Собеседник>: {message.decode()}')
            self.client_sock.close()


    def connect(self):
        try:
            self.ip = self.lineEdit.text()
            assert self.ip
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            self.client_sock.connect((self.ip, 9090))
            self.client_sock.close()
            print('Successfully connected')
        except Exception:
            print('Error while connecting')
            self.ip = ''


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())
