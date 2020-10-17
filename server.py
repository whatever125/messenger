from socketserver import BaseRequestHandler, ThreadingMixIn, TCPServer
import json


class Server:
    def __init__(self):
        self.host = host
        self.port = port
        self.socket = None
        self.need_terminate = False
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
    
    def close_server(self):
        if not self.socket:
            raise RuntimeError('Not running')
        self.socket.close()
        self.socket = None
        self.need_terminate = True
        self.worker_thread.join()
        self.worker_thread = None

    def worker_thread_function(self):
        self.mainloop()
    
    def mainloop(self):
        clients = []
        logins = {}
        auth_tokens = {}

        while True:
            if self.need_terminate:
                return

            try:
                conn, addr = self.socket.accept()  # check for new connections
            except OSError:
                pass  # timeout, do nothing
            else:
                print(f'Client connected: {str(addr)}')
                clients.append(conn)
            finally:  # check for incoming requests
                readable, writable, erroneous = [], [], []
                try:
                    readable, writable, erroneous = select.select(clients, clients, clients, 0)
                except:
                    pass  # if some client unexpectedly disconnected, do nothing
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
                            raise RuntimeError(f'Unknown JIM action: {request.action}')
                        self.__print_queue.put('Response:')
                        for resp in responses:
                            self.__print_queue.put(str(resp))
                            sleep(0.001)  # this magic solves problem with multiple jim messages in one socket message!!
                            client_socket.send(resp.to_bytes())
                    except BaseException as e:
                        self.__print_queue.put(f'Client disconnected: {client_socket.getpeername()}, {e}')
                        client_socket.close()
                        clients.remove(client_socket)
                        try:
                            del logins[client_socket]
                        except:
                            pass
                        if client_socket in writable:
                            writable.remove(client_socket)
    
    def check_online(self, request):
        client_login = request.datadict['user']['account_name']
        resp = JimResponse()
        if not self.storage.check_client_exists(client_login):  # unknown client - error
            resp.response = 400
        resp.set_field('error', f'No such client: {client_login}')
        elif client_login not in logins.values():  # known client arrived - need auth
            token = security.create_auth_token()
            auth_tokens[client_socket] = token
            resp = auth_server_message(token)
        elif client_socket in logins.keys() and \
            logins[client_socket] == client_login:  # existing client from same socket - ok
            client_time = request.datadict['time']
            client_ip = client_socket.getpeername()[0]
            self.storage.update_client(client_login, client_time, client_ip)
            resp.response = 200
        else:  # existing client from different ip - not correct
            resp.response = 400
            resp.set_field('error', 'Client already online')
        return resp
    
    def authentication(self, request):
        client_login = request.datadict['user']['account_name']
        client_hash = self.storage.get_client_hash(client_login)
        auth_token = auth_tokens[client_socket]
        del auth_tokens[client_socket]
        expected_digest = security.create_auth_digest(client_hash, auth_token)
        client_digest = request.datadict['user']['password']
        resp = JimResponse()
        if not security.check_auth_digest_equal(expected_digest, client_digest):
            resp.response = 402
            resp.set_field('error', 'Access denied')
        else:  # add client login to dict, update client in database
            logins[client_socket] = client_login
            client_time = request.datadict['time']
            client_ip = client_socket.getpeername()[0]
            self.storage.update_client(client_login, client_time, client_ip)
            resp.response = 200
        return resp
    
    def add_contact(self, request):
        client_login = logins[client_socket]
        contact_login = request.datadict['user_id']
        resp = JimResponse()
        if not self.storage.check_client_exists(contact_login):
            resp.response = 400
            resp.set_field('error', f'No such client: {contact_login}')
        elif self.storage.check_client_in_contacts(client_login, contact_login):
            resp.response = 400
            resp.set_field('error', f'Client already in contacts: {contact_login}')
        else:
            self.storage.add_client_to_contacts(client_login, contact_login)
            resp.response = 200
        return resp
    
    def del_contact(self, request):
        client_login = logins[client_socket]
        contact_login = request.datadict['user_id']
        resp = JimResponse()
        if not self.storage.check_client_exists(contact_login):
            resp.response = 400
            resp.set_field('error', f'No such client: {contact_login}')
        elif not self.storage.check_client_in_contacts(client_login, contact_login):
            resp.response = 400
            resp.set_field('error', f'Client not in contacts: {contact_login}')
        else:
            self.storage.del_client_from_contacts(client_login, contact_login)
            resp.response = 200
        return resp
    
    def get_contacts(self, request):
        client_login = logins[client_socket]
        client_contacts = self.storage.get_client_contacts(client_login)
        quantity_resp = JimResponse()
        quantity_resp.response = 202
        quantity_resp.set_field('quantity', len(client_contacts))
        responses.append(quantity_resp)
        for contact in client_contacts:
            contact_resp = JimResponse()
            contact_resp.set_field('action', 'contact_list')
            contact_resp.set_field('user_id', contact)
        return resp
    
    def handle_message(request):
        target_client_login = request.datadict['to']
        resp = JimResponse()
        for key, val in logins.items():
            if val == target_client_login:
                key.send(request.to_bytes())
                resp.response = 200
                break
        else:
            resp.response = 400
            resp.set_field('error', f'Client not online: {target_client_login}')
        return resp


class ThreadedTCPServer(ThreadingMixIn, TCPServer): 
    pass


if __name__ == '__main__':
    server = Server(args.listen_address, args.listen_port, storage_file)
    server.start()
