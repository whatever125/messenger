import socket

# Создание клиентского сокета
client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
client_sock.connect(('127.0.0.1', 55321)) # IP и порт сервера
# Отправка сообщения
client_sock.sendall(b'Hello, world')
# Получение ответа
data = client_sock.recv(1024)
# Закрытие клиентского сокета
client_sock.close()
# Вывод ответа
print('Received', repr(data))
