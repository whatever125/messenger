from socketserver import BaseRequestHandler, ThreadingMixIn, TCPServer
import json


class Server:
    def __init__(self):
        self.host = host
        self.port = port
        self.socket = None
        self.worker_thread = None

    def start(self):
        if self.socket:
            raise RuntimeError('Already started')
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1024)
        self.socket.settimeout(1024)
        self.worker_thread = Thread(target=self.worker_thread_function)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def worker_thread_function(self):
        self.mainloop()

    def mainloop(self):
        clients = []
        while True:
            try:
                client_socket, addr = self.socket.accept()
            except OSError:
                pass
            else:
                print(f'Client connected: {str(addr)}')
                clients.append(client_socket)
            finally:
                readable, writable, erroneous = [], [], []
                try:
                    readable, writable, erroneous = select.select(clients, clients, clients, 0)
                except:
                    pass
                for client_socket in readable:
                    try:
                        if client_socket not in writable:
                            continue
                        request = request_from_bytes(client_socket.recv(1024))
                        print(f'Request:\n{request}')
                        responses = []
                        if request.action == 'presence':
                            responses.append(self.check_online(request))
                        elif request.action == 'authenticate':
                            responses.append(self.authentication(request))
                        elif request.action == 'add_contact':
                            responses.append(self.add_contact(request))
                        elif request.action == 'del_contact':
                            responses.append(self.del_contact(request))
                        elif request.action == 'get_contacts':
                            responses.append(self.get_contacts(request))
                        elif request.action == 'msg':
                            responses.append(self.handle_message(request))
                        else:
                            raise RuntimeError(f'Unknown request: {request.action}')
                        print('Response:')
                        for resp in responses:
                            print(str(resp))
                            client_socket.send(resp.to_bytes())
                    except BaseException as e:
                        print(f'Client disconnected: {client_socket.getpeername()}, {e}')
                        client_socket.close()
                        clients.remove(client_socket)
                        if client_socket in writable:
                            writable.remove(client_socket)
    
    def check_online(self, request):
        reasp = None
        return resp
    
    def authentication(self, request):
        reasp = None
        return resp
    
    def add_contact(self, request):
        reasp = None
        return resp
    
    def del_contact(self, request):
        reasp = None
        return resp
    
    def get_contacts(self, request):
        reasp = None
        return resp
    
    def handle_message(request):
        reasp = None
        return resp


class ThreadedTCPServer(ThreadingMixIn, TCPServer): 
    pass


if __name__ == '__main__':
    server = Server(args.listen_address, args.listen_port, storage_file)
    server.start()
