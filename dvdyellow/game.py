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
        self.known_users = dict()

    def _make_user(self, uid):
        if uid not in self.known_users:
            self.known_users[uid] = User(self, uid)
        return self.known_users[uid]

    def process_events(self):
        self.client.receive_all()

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
        data = {
            'command': 'sign-out'
        }
        r = self.client.query(3, data)

        def result_processor():
            if r.response['status'] == 'ok':
                return True
            else:
                return False

        return AsyncQuery(lambda: r.check(), result_processor)

    def sign_up(self, login, password):
        data = {
            'command': 'sign-up',
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

    def get_signed_in_user(self):
        data = {
            'command': 'get-status'
        }
        r = self.client.query(3, data)

        def result_processor():
            if r.response['status'] == 'ok' and r.response['authenticated']:
                return self._make_user(r.response['id'])
            else:
                return None

        return AsyncQuery(lambda: r.check(), result_processor)

    def get_online_users(self):
        # TODO
        pass


class User:
    def __init__(self, session, user_id):
        self._uid = user_id
        self._name = None
        self.session = session

    @property
    def id(self):
        return self._uid

    @property
    def name(self):
        if self._name is None:
            data = {
                'command': 'get-name',
                'id': self._uid
            }
            r = self.session.client.query(3, data)

            def result_processor():
                if r.response['status'] == 'ok':
                    self._name = r.response['name']
                    return self._name
                else:
                    assert False

            return AsyncQuery(lambda: r.check(), result_processor)

        else:
            return AsyncQuery(lambda: True, lambda: self._name)

    @property
    def is_online(self):
        pass

    @property
    def get_status(self):
        pass
