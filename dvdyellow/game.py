"""
Here would be objects that client will use to play the game.

So classes like Board, WaitingRoom (from Client Game Interface)
will be here implemented.
"""
from sfml.system import sleep, milliseconds

from .network import Client


class AsyncQuery:
    def __init__(self, checker, result_getter):
        self.checker = checker
        self.result_getter = result_getter

    @property
    def ready(self):
        return self.checker()

    @property
    def result(self):
        while not self.checker():
            sleep(milliseconds(1))
        return self.result_getter()


def make_session(address, port=42371):
    client = Client(1)
    r = client.connect(address, port)
    return AsyncQuery(lambda: r.is_connected, lambda: Session(client))


class Session:
    def __init__(self, client):
        self.client = client

    def sign_in(self, login, password):
        data = {
            'command': 'sign-in',
            'username': login,
            'password': password
        }
        r = self.client.query(3, data)

        def result_processor():
            if r.response['status'] == 'ok':
                return True
            else:
                return False

        return AsyncQuery(lambda: r.check(), result_processor)

    def sign_out(self):
        pass

    def get_signed_in_user(self):
        data = {
            'command': 'get-status'
        }
        r = self.client.query(3, data)

        def result_processor():
            if r.response['status'] == 'ok' and r.response['authenticated']:
                return User(r.response['id'])
            else:
                return None

        return AsyncQuery(lambda: r.check(), result_processor)


class User:
    def __init__(self, user_id):
        self._uid = user_id