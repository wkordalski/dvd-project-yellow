import logging
import pickle
import struct
from collections import deque

import sfml as sf
import sfml.network as net

_hello_message_size = 64
_hello_message = b'dvdyellow hello: '
_accept_message = b'dvdyellow accepted'

_packet_length_size = 4

_logger = logging.getLogger("Network")


class Client:
    def __init__(self, api_version, blocking=False):
        self.api_version = api_version
        self.socket = net.TcpSocket()
        self.socket.blocking = blocking
        self.notification_handler = dict()
        self.buffer = b''
        self.current_packet_size = -1
        self.receiving_queries_queue = deque()

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

    def query(self, module, data):
        """
        Sends command to the server to specified module with some data.
        :param module: Module to which send the command.
        :param data: Parameter of the command - serialized before sending.
        :return: Temporary object to get the answer for the query.
        """
        msg = pickle.dumps((module, data))
        self.socket.send(struct.pack('I', len(msg)))
        self.socket.send(msg)

        class Query:
            def __init__(self, client):
                self.client = client
                self._response_object = None
                self._has_response = False

            @property
            def ready(self):
                return self._has_response

            def check(self):
                while not self._has_response:
                    if not self.client.receive():
                        return False
                return True

            @property
            def response(self):
                while not self.check():
                    pass
                return self._response_object

            def _set_response(self, value):
                self._response_object = value
                self._has_response = True

        qr = Query(self)
        self.receiving_queries_queue.append(qr)
        return qr

    def _receive_to_buffer(self, data_size):
        """
        Receives data from server.
        :param data_size: Amount of data to receive.
        :return: If the data was fully received.
        """
        length = data_size - len(self.buffer)
        if length > 0:
            try:
                received_data = self.socket.receive(length)
                length -= len(received_data)
                self.buffer += received_data
            except net.SocketNotReady:
                return False

        return length == 0

    def _get_buffer(self):
        msg = self.buffer
        self.buffer = b''
        self.current_packet_size = -1
        return msg

    def receive(self):
        """
        Processes a notification or response from server.
        :return: If there was something processed.
        """
        if self.current_packet_size == -1:
            if self._receive_to_buffer(_packet_length_size):
                msg = self.buffer
                self.buffer = b''
                self.current_packet_size = struct.unpack('I', msg)[0]

        if self.current_packet_size >= 0:
            if self._receive_to_buffer(self.current_packet_size):
                msg = self._get_buffer()
                channel, packet = pickle.loads(msg)
                if channel > 0:
                    # notification => run handler
                    handler = self.notification_handler.get(channel)
                    if handler:
                        handler(channel, packet)
                else:
                    # put packet to right receiver structure
                    self.receiving_queries_queue.popleft()._set_response(packet)
                return True

        return False

    def receive_all(self):
        """
        Processes all notifications and responses.
        :return: If there was any notification or response.
        """
        ret = False
        while self.receive():
            ret = True
        return ret

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

    def get_buffer(self):
        msg = self.buffer
        self.buffer = b''
        self.current_packet_size = -1
        return msg


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
            if self.selector.wait(sf.milliseconds(100)):
                clients_to_remove = set()
                unaccepted_to_remove = set()
                for client_id, data in self.clients.items():
                    if self.selector.is_ready(data.socket):
                        try:
                            if data.current_packet_size == -1:
                                if data.receive_to_buffer(_packet_length_size):
                                    msg = data.buffer
                                    data.buffer = b''
                                    data.current_packet_size = struct.unpack('I', msg)[0]
                            else:
                                if data.receive_to_buffer(data.current_packet_size):
                                    msg = data.get_buffer()
                                    module, packet = pickle.loads(msg)
                                    handler = self.query_handlers.get(module)
                                    if handler and \
                                            (not self.permission_checker or self.permission_checker(client_id, module)):
                                        result = handler(client_id, packet)
                                    else:
                                        result = None
                                    # send result
                                    # channel 0 => response to query
                                    msg = pickle.dumps((0, result))
                                    data.socket.send(struct.pack('I', len(msg)))
                                    data.socket.send(msg)
                                    data.current_packet_size = -1
                        except net.SocketDisconnected:
                            if self.disconnect_handler:
                                self.disconnect_handler(client_id)
                            self.selector.remove(data.socket)
                            clients_to_remove.add(client_id)

                for client_id, data in self.unaccepted.items():
                    if self.selector.is_ready(data.socket):
                        try:
                            if data.receive_to_buffer(_hello_message_size):
                                msg = data.get_buffer()
                                if msg[:len(_hello_message)] == _hello_message:
                                    try:
                                        api_version = int(pickle.loads(msg[len(_hello_message):]))
                                        if self.api_version_checker(api_version):
                                            data.socket.send(_accept_message.ljust(_hello_message_size, b'\x00'))
                                            self.clients[client_id] = data
                                            data.current_packet_size = -1
                                            unaccepted_to_remove.add(client_id)
                                            if self.accept_handler:
                                                self.accept_handler(client_id)
                                        else:
                                            data.socket.disconnect()
                                            self.selector.remove(data.socket)
                                            unaccepted_to_remove.add(client_id)
                                    except TypeError:
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
        old = self.query_handlers.get(module)
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

    def notify(self, client_id, channel, data):
        """
        Send notification to specified client.
        :param client_id: Client to which send the notification.
        :param channel: Channel by which send the notification.
        :param data: Data to be sent.
        """
        # send result
        msg = pickle.dumps((channel, data))
        client_data = self.clients.get(client_id)
        if not client_data:
            return      # notifying not existing client
        client_data.socket.send(struct.pack('I', len(msg)))
        client_data.socket.send(msg)

    def set_permission_checker(self, func):
        """
        Sets a function to verify if the query can be sent to specified module by specified client.
        :param func: Function that verifies the client or None to turn off the permission checker.
        :return: An old permission checker.
        """
        old = self.permission_checker
        self.permission_checker = func
        return old
