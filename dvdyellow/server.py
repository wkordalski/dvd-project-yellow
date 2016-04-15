"""
Server manager and server modules will be implemented here.
"""
from network import Server


class ServerManager:
    def __init__(self, port=42371):
        self.server = Server(lambda x: x == 1)
        self.port = port

        self.user_manager = UserManager(self.server)

    def run(self):
        """
        Runs server.
        """
        self.server.listen('0.0.0.0', self.port)

class _UserAuthenticationData:
    def __init__(self):
        self.authenticated = False
        self.username = ''

    def authenticate(self, username):
        self.authenticated = True
        self.username = username
        self.uid = 777

    def deauthenticate(self):
        self.authenticated = False
        self.username = ''
        self.uid = -1


class UserManager:
    def __init__(self, server):
        """
        Creates user manager.
        :param server:
        :param is_local:
        :return:
        """
        def permission_checker(client_id, module):
            return self._permission_checker(client_id, module)

        def query_handler(client_id, data):
            return self._query_handler(client_id, data)

        server.set_permission_checker(permission_checker)
        server.set_query_handler(3, query_handler)

        self.auth_status = dict()

    def _permission_checker(self, client_id, module):
        if module == 3:
            return True

        if client_id not in self.auth_status:
            return False

        return self.auth_status[client_id].authenticated

    def _query_handler(self, client_id, data):
        if 'command' not in data: return None

        if data['command'] == 'sign-in':
            return True
        elif data['command'] == 'sign-out':
            if client_id in self.auth_status:
                del self.auth_status[client_id]
                return True
            else:
                return False
        elif data['command'] == 'get-status':
            if client_id in self.auth_status:
                user_data = self.auth_status[client_id]
                if user_data.authenticated:
                    return {'authenticated': True, 'username': user_data.username, 'id': user_data.uid}
                else:
                    return {'authenticated': False}
            else:
                return {'authenticated': False}

        return None


class WaitingRoomManager:
    pass
