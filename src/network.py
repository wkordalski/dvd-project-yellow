import pickle
import sfml as sf


class Client:
    def __init__(self, api_version):
        raise NotImplementedError

    def connect(self, address, port):
        """
        Tries to connect to a server in a nonblocking manner.
        :param address: Network address of the server.
        :param port: Port on which the server runs.
        :return: Temporary object to query if connecting to client succeeded.
        """
        raise NotImplementedError

    def close(self):
        """
        Closes connection and frees all the resources.
        """
        raise NotImplementedError

    def query(self, module, command, data):
        """
        Sends command to the server to specified module with some data.
        :param module: Module to which send the command.
        :param command: Command to be sent.
        :param data: Parameter of the command - serialized before sending.
        :return: Temporary object to get the answer for the query.
        """
        raise NotImplementedError

    def receive_notifications(self, max_number_of_notifications=1000):
        """
        Processes notifications from servers.
        :param max_number_of_notifications: Maximal number of notifications to process.
        :return: Number of notifications processed.
        """
        raise NotImplementedError

    def set_notification_handler(self, channel, func):
        """
        Sets notifications handler for specified channel.
        :param channel: Channel to which set notifications handler.
        :param func: Function to be called on notifications or None if we want to turn off this channel processing.
        :return: Old notification handler.
        """
        raise NotImplementedError

    def ignore_notifications(self, channel):
        """
        Removes all notifications from buffer.
        :param channel: Channel which notifications remove.
        """
        raise NotImplementedError


class Server:
    def __init__(self):
        raise NotImplementedError

    def listen(self, address, port):
        """
        Starts listening on specified interface and port.
        :param address: Network address specifying interface.
        :param port: Port number.
        """
        raise NotImplementedError

    def close(self):
        """
        Stops listening and frees resources.
        """
        raise NotImplementedError

    def set_accept_handler(self, func):
        """
        Sets function called when some client gets connected.
        :param func: Function to be called or None if we want to turn off accept handler.
        :return: An old accept handler.
        """
        raise NotImplementedError

    def set_query_handler(self, module, func):
        """
        Sets query handler that is called when some client sends a query to the server.
        :param module: To which module assign the handler.
        :param func: The function that is called when query is received.
        :return: An old query handler.
        """
        raise NotImplementedError

    def notify(self, client, channel, data):
        """
        Send notification to specified client.
        :param client: Client to which send the notification.
        :param channel: Channel by which send the notification.
        :param data: Data to be sent.
        """
        raise NotImplementedError

    def set_permission_checker(self, func):
        """
        Sets a function to verify if the query can be sent to specified module by specified client.
        :param func: Function that verifies the client or None to turn off the permission checker.
        :return: An old permission checker.
        """
        raise NotImplementedError