"""
Here would be objects that client will use to play the game.

So classes like Board, WaitingRoom (from Client Game Interface)
will be here implemented.
"""
from sfml.system import sleep, milliseconds

from .network import Client


class AsyncQuery:
    """
    Represents a query that is done asynchronously.
    """
    def __init__(self, function, checker, result_getter):
        """
        Creates a asynchronous query.
        :param function: Function that initiates query
        (returns an object passed then to checker and result getter).
        :param checker: Function that checks if query is completed.
        :param result_getter: Function that returns result of the query.
        """
        self.function = function
        self.checker = checker
        self.result_getter = result_getter
        self.object = None
        self.started = False

    def run(self, *args, **kwargs):
        """
        Runs the query (calls function initiating query).
        :param args: Args passed to initiating query function.
        :param kwargs: Keyword args passed to initiating query function.
        :return: Asynchronous query (self).
        """
        old_started, self.started = self.started, True
        if old_started:
            raise AssertionError("Runned running query")

        self.object = self.function(*args, **kwargs)

        return self

    @property
    def ready(self):
        """
        If query is completed.
        """
        return self.checker(self.object)

    @property
    def result(self):
        """
        Returns the result (waits for completion if needed).
        :return:
        """
        while not self.checker(self.object):
            sleep(milliseconds(1))
        return self.result_getter(self.object)


class AsyncQueryChain:
    """
    Represents chain of asynchronous queries that must be run one after another.
    """
    def __init__(self, query, *args):
        """
        Creates chain of asynchronous queries.
        :param query: First query to run.
        :param args: Other queries to run.
        """
        self.queries = list(args)
        self.queries.insert(0, query)
        self.current = 0
        self.started = False
        self._result = None
        self._all_results = []
        self.error_reason = None
        self.error_result = None

    def run(self):
        """
        Run the queries sequentially.
        :return: Asynchronous query (self).
        """
        old_started, self.started = self.started, True
        if old_started:
            raise AssertionError("Runned running query")

        self.queries[0][0].run()

        return self

    @property
    def ready(self):
        """
        If the query are completed.
        """
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
        """
        Result of last query in the chain.
        """
        while not self.ready:
            sleep(milliseconds(1))
        return self._result
    
    @property
    def all_results(self):
        """
        Array of results of all queries in the chain.
        """
        while not self.ready:
            sleep(milliseconds(1))
        return self._all_results


def make_session(address, port=42371):
    """
    Deprecated: Connects to DVD Yellow game server and creates Session objects.
    Use Session.create(address, port) instead of this function.
    :param address: Address of the game server.
    :param port: Port number of the game server.
    :return: Asynchronous query object (returning Session object).
    """
    return Session.create(address, port)


def _check_result_ok(query):
    """
    Function that simply checks that query has finished w/o any errors.
    :param query: The query to check.
    :return: True if no errors were raised.
    """
    if query.response.get('status') == 'ok':
        return True
    else:
        return False


class Session:
    """
    Represents simple operations that can be done on the server.
    """
    def __init__(self, client):
        """
        Internal ctor for Session object. (To create Session object see make_session function).
        :param client: Network connection to use.
        """
        self.client = client
        self.known_users = dict()
        self.games = dict()     # id -> game object
        self.waiting_room = None
        self.on_game_found = None
        self.game_invitation = None             # type: ( User, bool->() ) -> ()
        self.game_invitation_cancelled = None   # type: ( User ) -> ()

        client.set_notification_handler(14, lambda ch, data: self._on_new_game(data))
        client.set_notification_handler(15, lambda ch, data: self._on_your_turn_in_game(data))
        client.set_notification_handler(16, lambda ch, data: self._on_invitation_notification(data))

    @classmethod
    def create(cls, address, port=42371):
        """
        Connects to DVD Yellow game server and creates Session objects.
        :param cls: Session class to use.
        :param address: Address of the game server.
        :param port: Port number of the game server.
        :return: Asynchronous query object (returning Session object).
        """
        client = Client(1)
        return AsyncQuery(lambda: client.connect(address, port), lambda r: r.is_connected, lambda _: Session(client)).run()

    def _make_user(self, uid):
        """
        Creates user object within the session.
        :param uid: User ID.
        :return: User object.
        """
        if uid not in self.known_users:
            self.known_users[uid] = User(self, uid)
        return self.known_users[uid]

    def _make_pawn(self, pawn_data):
        """
        Creates pawn object within the session.
        :param pawn_data: Data of the pawn (matrix).
        :return: Pawn object.
        """
        return Pawn(self, pawn_data)

    def process_events(self):
        """
        Processes network events and call related callbacks.
        """
        self.client.receive_all()

    def sign_in(self, login, password):
        """
        Signs in using specified authentication data.
        :param login: User's name.
        :param password: User's password.
        :return: Asynchronous query returning True if signing in succeeded, otherwise False.
        """
        data = {
            'command': 'sign-in',
            'username': login,
            'password': password
        }
        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), lambda r: _check_result_ok(r)).run()

    def sign_out(self):
        """
        Signs out from the server.
        :return: Asynchronous query returning True if signing out succeeded, otherwise False.
        """
        data = {
            'command': 'sign-out'
        }
        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), lambda r: _check_result_ok(r)).run()

    def sign_up(self, login, password):
        """
        Signs up using specified authentication data.
        :param login: User's name.
        :param password: User's password.
        :return: Asynchronous query returning True if signing up succeeded, otherwise False.
        """
        data = {
            'command': 'sign-up',
            'username': login,
            'password': password
        }
        return AsyncQuery(lambda: self.client.query(3, data), lambda r: r.check(), lambda r: _check_result_ok(r)).run()

    def get_signed_in_user(self):
        """
        Returns currently signed in user.
        :return: Asynchronous query returning currently signed in user.
        """
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
        """
        Called when new game is started with this user.
        :param data: Data from server.
        :return: Game object.
        """
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
        """
        Called when player gets his turn.
        :param data: Data from the server.
        """
        # TODO - call right game object (sb's move or finished)
        game_id = data['game-nr']
        game = self.games.get(game_id)
        if game: game._notification(data)

    def _on_invitation_notification(self, data):
        if data.get('notification') == 'random-game-challenge':
            if self.game_invitation:
                def set_status(accept):
                    data_inner = {
                        'command': 'accept-challenge' if accept else 'decline-challenge',
                        'opponent': data['opponent']
                    }

                    def process_result(r):
                        if accept:
                            if r.response.get('status') == 'ok':
                                return self._on_new_game(r.response)
                            else:
                                return None
                        else:
                            return _check_result_ok(r)

                    return AsyncQuery(lambda: self.client.query(5, data_inner), lambda r: r.check(), process_result).run()

                self.game_invitation(self._make_user(data.get('challenger')), set_status)

        elif data.get('notification') == 'challenge-backed':
            self.game_invitation_cancelled(self._make_user(data.get('challenger')))

    def get_waiting_room(self):
        """
        Gets (and creates if needed) Waiting Room object.
        :return: Asynchronous query returning Waiting Room object.
        """
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
            wr._on_change_status(channel, data)
        self.client.set_notification_handler(13, notifications_handler)

        def wr_setter(r):
            if _check_result_ok(r):
                wr.status = r.response['waiting-dict']
                self.waiting_room = wr
                return wr
            else:
                return None

        return AsyncQueryChain(
            (AsyncQuery(lambda: self.client.query(4, data_sign_in), lambda r: r.check(), _check_result_ok), lambda r: r),
            (AsyncQuery(lambda: self.client.query(4, data_listen), lambda r: r.check(), _check_result_ok), lambda r: r),
            (AsyncQuery(lambda: self.client.query(4, data_get), lambda r: r.check(), wr_setter), lambda r: r)
        ).run()

    def del_waiting_room(self):
        """
        Logs out from Waiting Room (and removes Waiting Room object).
        :return: Asynchronous query returning True if succeeded, otherwise False.
        """
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
            wr._on_change_status(channel, data)
        self.client.set_notification_handler(13, notifications_handler)

        def wr_setter(r):
            if _check_result_ok(r):
                self.waiting_room = None
                return True
            else:
                return False

        return AsyncQueryChain(
            (AsyncQuery(lambda: self.client.query(4, data_listen), lambda r: r.check(), _check_result_ok), lambda r: r),
            (AsyncQuery(lambda: self.client.query(4, data_sign_in), lambda r: r.check(), wr_setter), lambda r: r)
        ).run()

    def set_want_to_play(self):
        """
        Sets that player wants to play a game with some player.
        :return: Asynchronous query returning Game if somebody wants to play with one, None if there's no such player.
        """
        data = {
            'command': 'find-random-game'
        }

        def result_processor(r):
            # returns None if you have to wait returns game
            if not _check_result_ok(r) or 'game-status' not in r.response:
                raise AssertionError("Server error - FIXIT")
            if r.response['game-status'] == 'waiting':
                return None     # waiting...
            else:
                return self._on_new_game(r.response)

        return AsyncQuery(lambda: self.client.query(5, data), lambda r: r.check(), result_processor).run()

    def cancel_want_to_play(self):
        """
        Cancels player's want to play the game.
        :return: Asynchronous query returning True if succeeded, otherwise False.
        """
        data = {
            'command': 'quit-searching'
        }

        return AsyncQuery(lambda: self.client.query(5, data), lambda r: r.check(), _check_result_ok).run()

    def invite_to_game(self, user):
        data = {
            'command': 'challenge',
            'opponent': user.id
        }

        return AsyncQuery(lambda: self.session.client.query(5, data), lambda r: r.check(), _check_result_ok).run()

    def cancel_invite(self):
        data = {
            'command': 'cancel-challenge'
        }

        return AsyncQuery(lambda: self.session.client.query(5, data), lambda r: r.check(), _check_result_ok).run()


class User:
    """
    Represents a user in DVD Yellow system.
    """
    def __init__(self, session, user_id):
        """
        Creates user within specified session.
        :param session: Session within which create user object.
        :param user_id: User ID.
        """
        self._uid = user_id
        self._name = None
        self.session = session

    @property
    def id(self):
        """
        ID of the user.
        """
        return self._uid

    @property
    def name(self):
        """
        Asynchronous query for user name.
        """
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
        """
        Gets status of the user.
        :return: Asynchronous query returning user status.
        """
        return self.session.get_waiting_room().result.get_status_by_user(self)

    def set_status(self, status):
        """
        Sets status of the user.
        :param status: Status to set.
        :return: Asynchronous query returning True if status setting succeeded, otherwise False.
        """
        return self.session.get_waiting_room().result.set_status_by_user(self, status)


class WaitingRoom:
    """
    Represents waiting room of the server.
    """
    def __init__(self, session):
        """
        Creates waiting room within specified session.
        :param session: The session.
        """
        self.session = session
        self.status = dict()  # contains users' statuses
        self.status_changed = None

    def _on_change_status(self, channel, data):
        """
        Called when user changes status.
        :param channel: Notification channel.
        :param data: Data of the notification.
        """
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
        """
        Gets list of users in Waiting Room.
        :return: Returns asynchronous query returning list of users.
        """
        return AsyncQuery(lambda: None, lambda _: True,
                          lambda _: [self.session._make_user(uid) for uid in self.status.keys()]).run()

    def get_status_by_user(self, user):
        """
        Gets status of specified user.
        :param user: The user.
        :return: Asynchronous query returning user status.
        """
        if user.id in self.status:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: self.status[user.id]).run()
        else:
            return AsyncQuery(lambda: None, lambda _: True, lambda _: 'disconnected').run()

    def set_status_by_user(self, user, status):
        """
        Sets status of specified user.
        :param user: The user.
        :param status: New status.
        :return: Asynchronous query returning True if query succeeded, otherwise False.
        """
        data = {
            'command': 'set-status',
            'new-status': status,
            'uid': user.id,
        }

        return AsyncQuery(lambda: self.session.client.query(4, data), lambda r: r.check(), _check_result_ok).run()

    def get_ranking(self):
        data = {
            'command': 'get-ranking'
        }

        def parse_ranking(query):
            if query.response.get('status') == 'ok':
                ranking = query.response.get('ranking')
                return [(self.session._make_user(e['id']), e['points']) for e in ranking]
            else:
                return None

        return AsyncQuery(lambda: self.session.client.query(5, data), lambda r: r.check(), parse_ranking).run()


class Pawn:
    """
    Represents pawn.
    """
    def __init__(self, session, data):
        """
        Creates pawn within specified session.
        :param session: The session.
        :param data: Data of the pawn.
        """
        self.session = session
        self.data = data
        self.width = len(data)
        self.height = len(data[0])

    def get_pawn_point(self, x, y):
        """
        Check if point belongs to pawn.
        :param x: X coordinate.
        :param y: Y coordinate.
        :return: True if (x, y) belongs to the pawn.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.data[x][y]


class TransformablePawn:
    """
    Represents a pawn that can be rotated.
    """
    def __init__(self, pawn):
        """
        Creates transformable pawn based on other pawn.
        :param pawn: The base pawn.
        """
        self._rot = 0
        self._pawn = pawn

    def rotate_clockwise(self):
        """
        Rotates the pawn clockwise.
        """
        self._rot = (self._rot + 1) % 4

    def rotate_counter_clockwise(self):
        """
        Rotates the pawn counter clockwise.
        """
        self._rot = (self._rot + 3) % 4

    @property
    def rotation(self):
        """
        Returns rotation of the pawn.
        """
        return self._rot

    @property
    def width(self):
        """
        Returns the width of the pawn considering its rotation.
        """
        if self._rot % 2 == 0:
            return self._pawn.width
        else:
            return self._pawn.height

    @property
    def height(self):
        """
        Returns the height of the pawn considering its rotation.
        """
        if self._rot % 2 == 0:
            return self._pawn.height
        else:
            return self._pawn.width

    def get_pawn_point(self, x, y):
        """
        Check if point belongs to pawn.
        :param x: X coordinate.
        :param y: Y coordinate.
        :return: True if (x, y) belongs to the pawn.
        """
        if self._rot == 0:
            return self._pawn.get_pawn_point(x, y)
        if self._rot == 1:
            return self._pawn.get_pawn_point(y, self.width - x - 1)
        if self._rot == 2:
            return self._pawn.get_pawn_point(self.width - x - 1, self.height - y - 1)
        if self._rot == 3:
            return self._pawn.get_pawn_point(self.height - y - 1, x)


class Game:
    """
    Represents a game.
    """
    def __init__(self, session, gid, player_number, opponent, pawn, point_board):
        """
        Creates a game within specified session.
        :param session: The session.
        :param gid: Game ID.
        :param player_number: The role in the game (the first or the second player).
        :param opponent: The opponent user.
        :param pawn: The pawn used in the game.
        :param point_board: The board used in the game.
        """
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
        self.player_points = [0, 0]

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
        """
        Returns transformable pawn used in the game.
        :return: The transformable pawn.
        """
        return TransformablePawn(self.pawn)

    @property
    def is_finished(self):
        """
        Checks if the game is finished.
        :return: True if game is finished, otherwise False.
        """
        return self.result is not None

    def is_active_player(self):
        """
        Checks if signed-in user has currently its turn in the game.
        :return: True if it is the player turn, otherwise False.
        """
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
            print(r.response)
            if r and r.response.get('status') == 'ok':
                data = r.response
                if data.get('game-status') == 'opponents-turn':
                    self.player_points = data['player_points']
                    self.move_board = data.get('game_move_board')   # TODO - operator [] zamiast get
                elif data.get('game-status') == 'finished':
                    # game finished
                    if data['winner'] == 0:
                        self.result = 'draw'
                    elif data['winner'] == self.player_number:
                        self.result = 'won'
                    else:
                        self.result = 'defeated'
                    self.player_points = data['player_points']
                    self.move_board = data.get('game_move_board')   # TODO - operator [] zamiast get
                return True
            else:
                return False

        return AsyncQuery(lambda: self.session.client.query(5, data), lambda r: r.check(), result_processor).run()

    def abandon(self):
        """
        Abandons the game.
        :return: Asynchronous query returning True if abandoning succeeded.
        """
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
        """
        Called on notifications within game.
        :param data: Data from the server.
        """
        if data.get('notification') == 'game-finished':
            # game finished
            if data['winner'] == 0:
                self.result = 'draw'
            elif data['winner'] == self.player_number:
                self.result = 'won'
            else:
                self.result = 'defeated'
            self.player_points = data['player_points']
            self.move_board = data['game_move_board']
        elif data.get('notification') == 'your-new-turn':
            # your turn
            self.move_board = data['game_move_board']
            self.player_points = data['player_points']
            if self.on_your_turn:
                self.on_your_turn(self)
