import sys
import socket

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('messenger.ui', self)
        self.ip2 = '127.0.0.1'
        self.pushButton_2.clicked.connect(self.send)
        self.pushButton.clicked.connect(self.connect)
        self.pushButton_3.clicked.connect(self.check)

    def send(self):
        self.textEdit_2.append(f'<Вы>:{self.textEdit.toPlainText()}\n')
        self.client_sock.sendall(bytes(self.textEdit.toPlainText(), encoding='utf-8'))


    def connect(self):
        self.ip = self.lineEdit.text()
        #self.ip2 = self.lineEdit_2.text()
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_sock.connect((self.ip2, 55321))

    def check(self):
        message = self.client_sock.recv(1024)
        if message:
            self.textEdit_2.append(f'<Собеседник>:{str(message, encoding="utf-8")}\n')




if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())