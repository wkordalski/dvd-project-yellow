import pickle
import sfml as sf
import sfml.network as net

_hello_message = b'dvdyellow hello: '
_accept_message = b'dvdyellow accepted'


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
            address = net.IpAddress(address)

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
                self.missing = 64  # bytes
                self.accepted = False

                self._run()

                # States:
                # 0 - nothing done
                # 1 - waiting for connection
                # 2 - connected, hello message sent, waiting for response
                # 3 - got response - did everything

            @property
            def is_connected(self):
                return self.accepted if self._run() else False

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
                        self.accepted = True
                    else:
                        self.accepted = False
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


class Server:
    def __init__(self, api_version_checker):
        self.api_version_checker = api_version_checker
        self.listener = net.TcpListener()
        self.selector = net.SocketSelector()
        self.selector.add(self.listener)
        self.working = False
        self.clients = dict()
        self.query_handlers = dict()
        self.accept_handler = None
        self.disconnect_handler = None
        self.permission_checker = None

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
            address = net.IpAddress(address)

        self.listener.listen(address, port)
        self.working = True
        self._work()
        self._disconnect_all()

    def _work(self):
        while self.working:
            if self.selector.wait(sf.seconds(1)):
                to_remove = set()
                for client_id, socket in self.clients.items():
                    if self.selector.is_ready(socket):
                        try:
                            pass  # TODO - some data in
                        except net.SocketDisconnected:
                            # TODO - call handler
                            to_remove.add(client_id)

                for client_id in to_remove:
                    del self.clients[client_id]

                if self.selector.is_ready(self.listener):
                    pass  # TODO - some client connected

    def _disconnect_all(self):
        for client_id, socket in self.clients.items():
            self.selector.remove(socket)
            socket.disconnect()

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
