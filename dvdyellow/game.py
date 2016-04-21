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


def check_result_ok(query):
    if 'status' in query.result and query.result['status'] == 'ok':
        return True
    else:
        return False


def chain_queries(*args):
    # TODO
    pass

class Session:
    def __init__(self, client):
        self.client = client
        self.known_users = dict()
        self.waiting_room = None

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
        return AsyncQuery(lambda: r.check(), lambda: check_result_ok(r))

    def sign_out(self):
        data = {
            'command': 'sign-out'
        }

        r = self.client.query(3, data)
        return AsyncQuery(lambda: r.check(), lambda: check_result_ok(r))

    def sign_up(self, login, password):
        data = {
            'command': 'sign-up',
            'username': login,
            'password': password
        }

        r = self.client.query(3, data)
        return AsyncQuery(lambda: r.check(), lambda: check_result_ok(r))

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

    def get_waiting_room(self):
        data_sign_in = {
            'command': 'set-status',
            'new-status': 'connected'
        }

        data_listen = {
            'command': 'start-listening'
        }

        wr = WaitingRoom(self)

        def notifications_handler(channel, data):
            wr.on_change_status(channel, data)
        self.client.set_notification_handler(13, notifications_handler)

        r = self.client.query(4, data_sign_in)
        s = self.client.query(4, data_listen)

        return AsyncQuery(lambda: r.check and s.check,
                          lambda: wr if check_result_ok(r) and check_result_ok(s) else None)


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


class WaitingRoom:
    def __init__(self, session):
        self.session = session
        self.users = None     # contains active users
        self.status = dict()  # contains users' statuses
        self.status_changed = None

    def on_change_status(self, channel, data):
        # here should be updating internal tables and calling self.status_changed
        # TODO...

        if self.status_changed:
            # self.status_changed(user, old_status, new_status)
            pass
        pass

    def get_online_users(self):
        # returns list of User
        if self.users is None:
            # download users
            pass
        else:
            return AsyncQuery(lambda: True, lambda: [self.session._make_user(uid) for uid in self.users.keys()])

    def get_status_by_user(self, user):
        if user.id in self.status:
            return AsyncQuery(lambda: True, lambda: self.status[user.id])
        else:
            # call server
            pass

    def set_status(self):
        # send query to change status
        # returns AsyncQuery with True/False if it succeeded.
        pass
