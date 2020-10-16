from socketserver import BaseRequestHandler, ThreadingMixIn, TCPServer

class MyTCPHandler(BaseRequestHandler):
    def handle(self):
        # Получение сообщения
        data = self.request.recv(1024)
        # Отправка ответа
        self.request.sendall(data) 


class ThreadedTCPServer(ThreadingMixIn, TCPServer): 
    pass


if __name__ == '__main__':
    # IP и порт сервера
    host = 'localhost'
    port = 55321
    # Многопоточный TCP сервер
    with ThreadedTCPServer((host, port), MyTCPHandler) as srv:
        srv.serve_forever()
