import pickle
from unittest.case import TestCase
from threading import Thread

import sfml as sf
import sfml.network as net
from sfml.system import sleep, milliseconds

_hello_message_size = 64
_hello_message = b'dvdyellow hello: '
_accept_message = b'dvdyellow accepted'

_packet_length_size = 4

class Client:
    def __init__(self, api_version, blocking=False):
        self.api_version = api_version
        self.socket = net.TcpSocket()
        self.socket.blocking = blocking
        self.notification_handler = dict()

    def connect(self, address, port):
        """
        Tries to connect to a server in a nonblocking manner.
        :param address: Network address of the server.
        :param port: Port on which the server runs.
        :return: Temporary object to query if connecting to client succeeded.
        """
        if isinstance(address, str):
            address = net.IpAddress.from_string(address)

        class Connector:
            """
            Waits for connection to the server and does API version checking
            in a non-blocking way.
            """
            def __init__(self, client, target_address, target_port):
                self.client = client
                self.address = target_address
                self.port = target_port
                self.state = 0  # nothing done
                self.buffer = b''
                self.missing = _hello_message_size
                self._accepted = False

                self._run()

                # States:
                # 0 - nothing done
                # 1 - waiting for connection
                # 2 - connected, hello message sent, waiting for response
                # 3 - got response - did everything

            @property
            def is_connected(self):
                return self._accepted if self._run() else False

            def _run(self):
                """
                Runs some stuff to check if connected...
                :return: True if connecting process is finished.
                """
                if self.state == 0 or self.state == 1:
                    try:
                        self.client.socket.connect(self.address, self.port)
                    except net.SocketNotReady:
                        return False
                    # connected - send hello message
                    message = (_hello_message + pickle.dumps(self.client.api_version)).ljust(64, b'\x00')
                    self.client.socket.send(message)
                    self.state = 2

                if self.state == 2:
                    try:
                        tmp = self.client.socket.receive(self.missing)
                        self.missing -= len(tmp)
                        self.buffer += tmp
                    except net.SocketNotReady:
                        return False

                    if self.missing > 0:
                        return False

                    # check message => API compatibility
                    if self.buffer == _accept_message.ljust(64, b'\x00'):
                        self._accepted = True
                    else:
                        self._accepted = False
                        self.client.socket.disconnect()
                    self.state = 3
                    return True

                if self.state == 3:
                    return True

                return False

        connector = Connector(self, address, port)
        return connector

    def disconnect(self):
        """
        Closes connection and frees all the resources.
        """
        self.socket.disconnect()

    def query(self, module, command, data):
        """
        Sends command to the server to specified module with some data.
        :param module: Module to which send the command.
        :param command: Command to be sent.
        :param data: Parameter of the command - serialized before sending.
        :return: Temporary object to get the answer for the query.
        """
        # TODO - send data with socket - some notifications could be triggered
        raise NotImplementedError

    def receive(self):
        """
        Processes notifications and responses from servers.
        :return: Number of notifications processed.
        """
        # TODO - receives notifications and responses from server
        raise NotImplementedError

    def set_notification_handler(self, channel, func):
        """
        Sets notifications handler for specified channel.
        :param channel: Channel to which set notifications handler.
        :param func: Function to be called on notifications or None if we want to turn off this channel processing.
        :return: Old notification handler.
        """
        old = self.notification_handler.get(channel)
        self.notification_handler[channel] = func
        return old


class _ClientData:
    def __init__(self, client_id, socket):
        self.client_id = client_id
        self.socket = socket
        self.buffer = b''
        self.current_packet_size = -1

    def receive_to_buffer(self, data_size):
        """
        Receives data from client.
        :param data_size: Amount of data to receive.
        :return: If the data was fully received.
        """
        length = data_size - len(self.buffer)
        if length > 0:
            received_data = self.socket.receive(length)
            length -= len(received_data)
            self.buffer += received_data

        return length == 0


class Server:
    def __init__(self, api_version_checker):
        self.api_version_checker = api_version_checker
        self.listener = net.TcpListener()
        self.selector = net.SocketSelector()
        self.working = False
        self.query_handlers = dict()
        self.accept_handler = None
        self.disconnect_handler = None
        self.permission_checker = None

        self.clients = dict()
        self.unaccepted = dict()

        def seq_id_generator(start):
            while True:
                yield start
                start += 1
        self.id_generator = seq_id_generator(7)

    def listen(self, address, port):
        """
        Starts listening on specified interface and port.
        :param address: Network address specifying interface.
        :param port: Port number.
        """
        if isinstance(address, str):
            address = net.IpAddress.from_string(address)

        self.listener.listen(port)
        self.selector.add(self.listener)
        self.working = True
        self._work()
        self._disconnect_all()

    def _work(self):
        while self.working:
            if self.selector.wait(sf.seconds(1)):
                clients_to_remove = set()
                unaccepted_to_remove = set()
                for client_id, data in self.clients.items():
                    if self.selector.is_ready(data.socket):
                        try:
                            if data.current_packet_size == -1:
                                if data.receive_to_buffer(_packet_length_size):
                                    pass
                            else:
                                if data.receive_to_buffer(data.current_packet_size):
                                    pass
                        except net.SocketDisconnected:
                            # TODO - call handler
                            self.selector.remove(data.socket)
                            clients_to_remove.add(client_id)

                for client_id, data in self.unaccepted.items():
                    if self.selector.is_ready(data.socket):
                        try:
                            if data.receive_to_buffer(_hello_message_size):
                                msg = data.buffer
                                data.buffer = b''
                                if msg[:len(_hello_message)] == _hello_message:
                                    try:
                                        api_version = int(pickle.loads(msg[len(_hello_message):]))
                                    except TypeError:
                                        data.socket.disconnect()
                                        self.selector.remove(data.socket)
                                        unaccepted_to_remove.add(client_id)
                                    if self.api_version_checker(api_version):
                                        data.socket.send(_accept_message.ljust(_hello_message_size, b'\x00'))
                                        self.clients[client_id] = data
                                        unaccepted_to_remove.add(client_id)
                                        if self.accept_handler: self.accept_handler(client_id)
                                    else:
                                        data.socket.disconnect()
                                        self.selector.remove(data.socket)
                                        unaccepted_to_remove.add(client_id)
                                else:
                                    data.socket.disconnect()
                                    self.selector.remove(data.socket)
                                    unaccepted_to_remove.add(client_id)
                        except net.SocketDisconnected:
                            self.selector.remove(data.socket)
                            unaccepted_to_remove.add(client_id)

                for client_id in clients_to_remove:
                    del self.clients[client_id]

                for client_id in unaccepted_to_remove:

                    del self.unaccepted[client_id]

                if self.selector.is_ready(self.listener):
                    socket = self.listener.accept()
                    client_id = next(self.id_generator)
                    self.unaccepted[client_id] = _ClientData(client_id, socket)
                    self.selector.add(socket)

    def _disconnect_all(self):
        for client_id, data in self.clients.items():
            self.selector.remove(data.socket)
            data.socket.disconnect()

        self.clients.clear()

    def close(self):
        """
        Stops listening and frees resources.
        """
        self.working = False

    def set_accept_handler(self, func):
        """
        Sets function called when some client gets connected.
        :param func: Function to be called or None if we want to turn off accept handler.
        :return: An old accept handler.
        """
        old = self.accept_handler
        self.accept_handler = func
        return old

    def set_query_handler(self, module, func):
        """
        Sets query handler that is called when some client sends a query to the server.
        :param module: To which module assign the handler.
        :param func: The function that is called when query is received.
        :return: An old query handler.
        """
        old = self.query_handlers.get(module, default=None)
        self.query_handlers[module] = func
        return old

    def set_disconnect_handler(self, func):
        """
        Sets function called when some client gets disconnected.
        :param func: Function called on client disconnect.
        :return: An old disconnect handler.
        """
        old = self.disconnect_handler
        self.disconnect_handler = func
        return old

    def notify(self, client, channel, data):
        """
        Send notification to specified client.
        :param client: Client to which send the notification.
        :param channel: Channel by which send the notification.
        :param data: Data to be sent.
        """
        # TODO - send data to client
        raise NotImplementedError

    def set_permission_checker(self, func):
        """
        Sets a function to verify if the query can be sent to specified module by specified client.
        :param func: Function that verifies the client or None to turn off the permission checker.
        :return: An old permission checker.
        """
        old = self.permission_checker
        self.permission_checker = func
        return old


class NetworkTests(TestCase):
    def test_connect(self):
        server = Server(lambda x: True)
        client = Client(123)
        srv_th = Thread(target=Server.listen, args=(server, '127.0.0.1', 1234), daemon=False)
        srv_th.start()

        c = client.connect('127.0.0.1', 1234)
        for i in range(30):
            if c.is_connected: break
            sleep(milliseconds(100))
        try:
            self.assertTrue(c.is_connected)
        except AssertionError:
            client.disconnect()
            server.close()
            srv_th.join(timeout=2.)
            raise

        client.disconnect()
        server.close()
        srv_th.join(timeout=2.)
        self.assertFalse(srv_th.is_alive())
