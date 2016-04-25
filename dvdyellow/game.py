"""
Here would be objects that client will use to play the game.

So classes like Board, WaitingRoom (from Client Game Interface)
will be here implemented.
"""
from sfml.system import sleep, milliseconds

from .network import Client


class AsyncQuery:
    def __init__(self, function, checker, result_getter):
        self.function = function
        self.checker = checker
        self.result_getter = result_getter
        self.object = None
        self.started = False

    def run(self, *args, **kwargs):
        old_started, self.started = self.started, True
        if old_started:
            raise AssertionError("Runned running query")

        self.object = self.function(*args, **kwargs)

        return self

    @property
    def ready(self):
        return self.checker(self.object)

    @property
    def result(self):
        while not self.checker(self.object):
            sleep(milliseconds(1))
        return self.result_getter(self.object)


class AsyncQueryChain:
    def __init__(self, query, *args):
        self.queries = list(args)
        self.queries.insert(0, query)
        self.current = 0
        self.started = False
        self._result = None
        self._all_results = []
        self.error_reason = None
        self.error_result = None

    def run(self):
        old_started, self.started = self.started, True
        if old_started:
            raise AssertionError("Runned running query")

        self.queries[0][0].run()

        return self

    @property
    def ready(self):
        if self.current >= len(self.queries):
            return True

        while True:
            # check if current is done
            if self.queries[self.current][0].ready:
                # get result, verify and run next
                result = self.queries[self.current][0].result
                self._all_results.append(result)
                if self.queries[self.current][1] and not self.queries[self.current][1](self._all_results):
                    self._result = self.error_result
                    self.current = len(self.queries)
                    return True
                else:
                    self.current += 1
                    if self.current >= len(self.queries):
                        self._result = result
                        return True
                    else:
                        self.queries[self.current][0].run()
                        continue
            else:
                return False

    @property
    def result(self):
        while not self.ready:
            sleep(milliseconds(1))
        return self._result
    
    @property
    def all_results(self):
        while not self.ready:
            sleep(milliseconds(1))
        return self._all_results


def make_session(address, port=42371):
    client = Client(1)
    return AsyncQuery(lambda: client.connect(address, port), lambda r: r.is_connected, lambda _: Session(client)).run()


def check_result_ok(query):
    if query.response.get('status') == 'ok':
        return True
    else:
        return False


class Session:
    def __init__(self, client):
        self.client = client
        self.known_users = dict()
        self.games = dict()     # id -> game object
        self.waiting_room = None
        self.on_game_found = None

        client.set_notification_handler(14, lambda ch, data: self._on_new_game(data))
        client.set_notification_handler(15, lambda ch, data: self._on_your_turn_in_game(data))

    def _make_user(self, uid):
        if uid not in self.known_users:
            self.known_users[uid] = User(self, uid)
        return self.known_users[uid]

    def _make_pawn(self, pawn_data):
        return Pawn(self, pawn_data)

    def process_events(self):
        self.client.receive_all()

    def sign_in(self, login, password):
        data = {
            'command': 'sign-in',
            'username': login,
            'password': password
        }
        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), lambda r: check_result_ok(r)).run()

    def sign_out(self):
        data = {
            'command': 'sign-out'
        }
        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), lambda r: check_result_ok(r)).run()

    def sign_up(self, login, password):
        data = {
            'command': 'sign-up',
            'username': login,
            'password': password
        }
        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), lambda r: check_result_ok(r)).run()

    def get_signed_in_user(self):
        data = {
            'command': 'get-status'
        }

        def result_processor(r):
            if r.response['status'] == 'ok' and r.response['authenticated']:
                return self._make_user(r.response['id'])
            else:
                return None

        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), result_processor).run()

    def _on_new_game(self, data):
        game_id = data['game-nr']
        game = Game(session=self,
                    gid=game_id,
                    opponent=self._make_user(data['opponent-id']),
                    pawn=self._make_pawn(data['game-pawn']),
                    point_board=data['game-board'],
                    player_number=data['player-number'])

        self.games[game_id] = game
        print(game.pawn)
        if self.on_game_found:
            self.on_game_found(game)
        return game

    def _on_your_turn_in_game(self, data):
        # TODO - call right game object (sb's move or finished)
        game_id = data['game-nr']
        game = self.games.get(game_id)
        if game: game._notification(data)

    def get_waiting_room(self):
        if self.waiting_room:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: self.waiting_room)

        data_sign_in = {
            'command': 'set-status',
            'new-status': 'connected'
        }

        data_listen = {
            'command': 'start-listening'
        }

        data_get = {
            'command': 'get-waiting-room'
        }

        wr = WaitingRoom(self)

        def notifications_handler(channel, data):
            wr.on_change_status(channel, data)
        self.client.set_notification_handler(13, notifications_handler)

        def wr_setter(r):
            if check_result_ok(r):
                wr.status = r.response['waiting-dict']
                self.waiting_room = wr
                return wr
            else:
                return None

        return AsyncQueryChain(
            (AsyncQuery(lambda: self.client.query(4, data_sign_in), lambda r: r.check(), check_result_ok), lambda r: r),
            (AsyncQuery(lambda: self.client.query(4, data_listen), lambda r: r.check(), check_result_ok), lambda r: r),
            (AsyncQuery(lambda: self.client.query(4, data_get), lambda r: r.check(), wr_setter), lambda r: r)
        ).run()

    def del_waiting_room(self):
        if not self.waiting_room:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: None)

        data_sign_in = {
            'command': 'set-status',
            'new-status': 'disconnected'
        }

        data_listen = {
            'command': 'stop-listening'
        }

        wr = WaitingRoom(self)

        def notifications_handler(channel, data):
            wr.on_change_status(channel, data)
        self.client.set_notification_handler(13, notifications_handler)

        def wr_setter(r):
            if check_result_ok(r):
                self.waiting_room = None
                return True
            else:
                return False

        return AsyncQueryChain(
            (AsyncQuery(lambda: self.client.query(4, data_listen), lambda r: r.check(), check_result_ok), lambda r: r),
            (AsyncQuery(lambda: self.client.query(4, data_sign_in), lambda r: r.check(), wr_setter), lambda r: r)
        ).run()

    def set_want_to_play(self):
        data = {
            'command': 'find-random-game'
        }

        def result_processor(r):
            # returns None if you have to wait returns game
            if not check_result_ok(r) or 'game-status' not in r.response:
                raise AssertionError("Server error - FIXIT")
            if r.response['game-status'] == 'waiting':
                return None     # waiting...
            else:
                return self._on_new_game(r.response)

        return AsyncQuery(lambda: self.client.query(5, data), lambda r: r.check(), result_processor).run()

    def cancel_want_to_play(self):
        data = {
            'command': 'quit-searching'
        }

        return AsyncQuery(lambda: self.client.query(5, data), lambda r: r.check(), check_result_ok).run()


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

            def result_processor(r):
                if r.response['status'] == 'ok':
                    self._name = r.response['name']
                    return self._name
                else:
                    assert False

            return AsyncQuery(lambda: self.session.client.query(3, data), lambda r: r.check(), result_processor).run()

        else:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: self._name).run()

    def get_status(self):
        return self.session.get_waiting_room().result.get_status_by_user(self)

    def set_status(self, status):
        return self.session.get_waiting_room().result.set_status_by_user(self, status)


class WaitingRoom:
    def __init__(self, session):
        self.session = session
        self.status = dict()  # contains users' statuses
        self.status_changed = None

    def on_change_status(self, channel, data):
        # here should be updating internal tables and calling self.status_changed
        if data['notification'] == 'status-change':
            uid = data.get('user')
            status = data.get('status')
            old_status = self.status[uid] if uid in self.status else 'disconnected'

            if status == 'disconnected':
                del self.status[uid]
            else:
                self.status[uid] = status

        if self.status_changed:
            self.status_changed(self.session._make_user(uid), old_status, status)

    def get_online_users(self):
        # returns list of User
        return AsyncQuery(lambda: None, lambda _: True,
                          lambda _: [self.session._make_user(uid) for uid in self.status.keys()]).run()

    def get_status_by_user(self, user):
        if user.id in self.status:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: self.status[user.id]).run()
        else:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: 'disconnected').run()

    def set_status_by_user(self, user, status):
        # send query to change status
        data = {
            'command': 'set-status',
            'new-status': status,
            'uid': user.id,
        }

        return AsyncQuery(lambda: self.session.client.query(4, data), lambda r: r.check(), check_result_ok).run()


class Pawn:
    def __init__(self, session, data):
        self.session = session
        self.data = data
        self.width = len(data)
        self.height = len(data[0])

    def get_pawn_point(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.data[x][y]


class TransformablePawn:
    def __init__(self, pawn):
        self._rot = 0
        self._pawn = pawn
        pass

    def rotate_clockwise(self):
        self._rot = (self._rot + 1) % 4

    @property
    def rotation(self):
        return self._rot

    @property
    def width(self):
        if self._rot % 2 == 0:
            return self._pawn.width
        else:
            return self._pawn.height

    @property
    def height(self):
        if self._rot % 2 == 0:
            return self._pawn.height
        else:
            return self._pawn.width

    def get_pawn_point(self, x, y):
        if self._rot == 0:
            return self._pawn.get_pawn_point(x, y)
        if self._rot == 1:
            return self._pawn.get_pawn_point(y, self.width - x - 1)
        if self._rot == 2:
            return self._pawn.get_pawn_point(self.width - x - 1, self.height - y - 1)
        if self._rot == 3:
            return self._pawn.get_pawn_point(self.height - y - 1, x)


class Game:
    def __init__(self, session, gid, player_number, opponent, pawn, point_board):
        self.session = session
        self.gid = gid
        self.player_number = player_number
        self.opponent = opponent
        self.pawn = pawn
        self.point_board = point_board
        self.width = len(point_board)
        self.height = len(point_board[0])
        self.on_your_turn = None   # what to do on your turn (Game -> ())
        self.on_finish = None      # what to do when game is finished (Game -> ())
        self.result = None         # 'won', 'defeated' or 'draw' when game finished
        self.move_board = [[-3 if self.point_board[i][j] == 0 else 0 for j in range(self.height)] for i in range(self.width)]
        self.active_player = 1

    def get_field(self, x, y):
        """
        Gets information about specific field.
        First element of result is:
          0     - if player can put there the pawn
          1/2   - if player 1/2 got this field
          -1/-2 - if player 1/2 blocked this field.
          -3    - if this field is ungettable
        :param x: X coordinate of the field.
        :param y: Y coordinate of the field.
        :return: Tuple containing who has the field and pointing information.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return -3, 0
        return self.move_board[x][y], self.point_board[x][y]

    def get_transformable_pawn(self):
        return TransformablePawn(self.pawn)

    @property
    def is_finished(self):
        return self.result is not None

    def is_active_player(self):
        return self.active_player == self.player_number and not self.is_finished

    def move(self, point, pawn):
        """
        Makes move. It puts pawn (TransformablePawn) at specified point.
        :param point: Where to put the pawn.
        :param pawn: TransformablePawn to put.
        :return: Query which result is if move command succeeded.
        """
        if self.is_finished:
            raise AssertionError("The game was finished!")
        data = {
            'command': 'move',
            'game-nr': self.gid,
            'player-nr': self.player_number,
            'x': point[0], 'y': point[1],
            'rotation': pawn.rotation
        }

        def result_processor(r):
            if r and r.response.get('status') == 'ok':
                if r.response.get('game-status') == 'opponent-turn':
                    self.player_points = data['player_points']
                    self.move_board = data.get('game_move_board')   # TODO - operator [] zamiast get
                elif r.response.get('game-status') == 'game-finished':
                    # game finished
                    if data['winner'] == 0:
                        self.result = 'draw'
                    elif data['winner'] == self.player_number:
                        self.result = 'won'
                    else:
                        self.result = 'defeat'
                    self.player_points = data['player_points']
                    self.move_board = data.get('game_move_board')   # TODO - operator [] zamiast get
                return True
            else:
                return False

        return AsyncQuery(lambda: self.session.client.query(5, data), lambda r: r.check(), result_processor).run()

    def abandon(self):
        if self.is_finished:
            raise AssertionError("The game was finished!")
        data = {
            'command': 'abandon-game',
            'game-nr': self.gid,
            'player-nr': self.player_number,
        }

        def result_processor(r):
            if r and r.response.get('status') == 'ok':
                self.result = 'defeated'
                return True
            else:
                return False

        return AsyncQuery(lambda: self.session.client.query(5, data), lambda r: r.check(), result_processor).run()

    def _notification(self, data):
        if data.get('notification') == 'game-finished':
            # game finished
            if data['winner'] == 0:
                self.result = 'draw'
            elif data['winner'] == self.player_number:
                self.result = 'won'
            else:
                self.result = 'defeat'
            self.player_points = data['player_points']
            self.move_board = data.get('game_move_board')   # TODO - operator [] zamiast get
        elif data.get('notification') == 'your-new-turn':
            # your turn
            self.move_board = data['game_move_board']
            self.player_points = data['player_points']
            if self.on_your_turn:
                self.on_your_turn(self)
