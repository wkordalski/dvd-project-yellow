"""
Here would be objects that client will use to play the game.

So classes like Board, WaitingRoom (from Client Game Interface)
will be here implemented.
"""
from network import Client


def connect_client(address, port=42371):
    client = Client(1)
    return client.connect(address, port)


class AsyncQuery:
    def __init__(self, checker, result_getter):
        self.checker = checker
        self.result_getter = result_getter

    @property
    def ready(self):
        return self.checker()

    @property
    def result(self):
        while not self.checker: pass
        return self.result_getter()


class Server:
    def __init__(self, connector):
        self.client = connector.client

    def sign_in(self, login, password):
        data = {
            'command': 'sign-in',
            'username': login,
            'password': password
        }
        r = self.client.query(3, data)
        return AsyncQuery(lambda: r.check(), lambda: True if r.response == True else False)

    def get_logged_user(self):
        data = {
            'command': 'get-status'
        }
        r = self.client.query(3, data)

        def result_processor():
            if not r.response:
                return None
            else:
                if r.response['authenticated']:
                    return User(r.response['id'])
                else:
                    return None

        return AsyncQuery(lambda: r.check(), result_processor)


class User:
    def __init__(self, user_id):
        self._uid = user_id