"""
Server manager and server modules will be implemented here.
"""
import argparse
import logging
import os

import yaml
from functools import reduce

import random
from appdirs import AppDirs
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm.session import sessionmaker

from .orm import User, GameBoard, GamePawn, create_schemes
from .network import Server


class ServerManager:
    def __init__(self, target_configuration=None, config_file=None, config_object=None):
        self.server = Server(lambda x: x == 1)
        self.logger = logging.getLogger("ServerManager")
        self.dirs = AppDirs('dvdyellow', appauthor='yellow-team', multipath=True)
        self.config = None

        self._setup_server_configuration(target_configuration, config_file, config_object)
        self._setup_database()

        self.user_manager = UserManager(self.server, self.db_session)
        self.waiting_room = WaitingRoomManager(self)
        self.game_manager = GameManager(self.server, self.user_manager, self.db_session)

        self.on_run = None

    def _load_config_file(self, path):
        try:
            f = open(path)
            self.config = yaml.safe_load(f)
            f.close()
        except IOError:
            self.logger.error("Configuration file '%s' exists, but is not readable.", path)
            raise  # TODO - should be another exception...
        except yaml.YAMLError as e:
            self.logger.error("Error in configuration file: %s", e)
            raise  # TODO - should be another exception...

    def _load_configuration(self, directories):
        for path in directories:
            conf_file = os.path.join(path, 'server.yml')
            if not os.path.isfile(conf_file):
                continue
            self._load_config_file(conf_file)

    def get_config_entry(self, getter, default, is_empty_default=False):
        """
        Returns entry value from configuration.
        :param getter: Function getting value from configuration object or string with dot-separated ids.
        :param default: Default values if nowhere such entry is present.
        :param is_empty_default: If value is an empty string and is_empty_default is set, returned is the default value.
        :return: The value of such entry.
        """
        if isinstance(getter, str):
            path_elements = getter.split('.')

            def getter(c):
                return reduce(lambda d, k: d[k], path_elements, c)

        for config in self.configurations:
            if not config:
                continue
            try:
                r = getter(config)
                if r == '' and is_empty_default:
                    return default
                else:
                    return r
            except KeyError:
                pass

        return default

    def _setup_server_configuration(self, target_configuration=None, config_file=None, config_object=None):
        """
        Sets-up server configuration - reads configuration files and parses some server options
        :param target_configuration: Name of configuration to use.
        :param config_file: Configuration file to read instead of the default one.
        :param config_object: Configuration data put directly into server module.
        """
        if not config_file:
            config_paths = self.dirs.user_config_dir.split(os.pathsep) + self.dirs.site_config_dir.split(os.pathsep)
            self._load_configuration(filter(None, config_paths))
        else:
            self._load_config_file(config_file)

        if target_configuration and self.config:
            target_cfg = self.config[target_configuration] if target_configuration in self.config else None
        else:
            target_cfg = None
        default_cfg = self.config['default'] if self.config and 'default' in self.config else None
        # configurations - first is most important
        self.configurations = list(filter(None, [config_object, target_cfg, default_cfg]))

        #
        # NETWORK SETTINGS
        #
        self.port = self.get_config_entry('network.port', 42371)

        #
        # DATABASE SETTINGS
        #
        self.db_url = URL(
            self.get_config_entry('database.driver', 'sqlite'),
            self.get_config_entry('database.username', None, is_empty_default=True),
            self.get_config_entry('database.password', None, is_empty_default=True),
            self.get_config_entry('database.host', None, is_empty_default=True),
            self.get_config_entry('database.port', None, is_empty_default=True),
            self.get_config_entry('database.name', None, is_empty_default=True),
            self.get_config_entry('database.options', None, is_empty_default=True)
        )

    def _setup_database(self):
        self.db = create_engine(self.db_url)
        self.db_connection = self.db.connect()
        create_schemes(self.db)

        self.db_session_type = sessionmaker(bind=self.db)
        self.db_session = self.db_session_type()

    def run(self):
        """
        Runs server.
        """
        if self.on_run:
            self.on_run()

        try:
            self.logger.info("Starting listening...")
            self.server.listen('0.0.0.0', self.port)
        except KeyboardInterrupt:
            self.server.close()

        self.logger.info("Finalizing server,,,")
        self._finalize()

    def stop(self):
        self.server.close()

    def _finalize(self):
        self.db_connection.close()


class _UserAuthenticationData:
    def __init__(self, username, uid):
        self.username = username
        self.uid = uid


class UserManager:
    def __init__(self, server, db_session):
        """
        Creates user manager.
        :param server: server used to communication
        :param db_session: connection to database
        :return:
        """
        self.disconnect_handlers = []

        def disconnect_handler(client_id):
            return self._on_client_disconnect(client_id)

        def permission_checker(client_id, module):
            return self._permission_checker(client_id, module)

        def query_handler(client_id, data):
            return self._query_handler(client_id, data)

        server.set_disconnect_handler(disconnect_handler)
        server.set_permission_checker(permission_checker)
        server.set_query_handler(3, query_handler)

        self.database_session = db_session
        self.auth_status = dict()
        self.client_users = dict()

    def _permission_checker(self, client_id, module):
        if module == 3:
            return True

        if client_id in self.auth_status:
            return True

        return False

    def _on_client_disconnect(self, client_id):
        for handler in self.disconnect_handlers:
            if handler:
                handler(client_id)

        if client_id in self.auth_status:
            del self.client_users[self.auth_status[client_id].uid]
            del self.auth_status[client_id]

    def get_users_client(self, user_id):
        return self.client_users.get(user_id)

    def get_clients_user(self, client_id):
        return self.auth_status[client_id].uid

    def _query_handler(self, client_id, data):
        """
        :param client_id: id of client which sent the query
        :param data: query to server
        :return:
        """
        if 'command' not in data:
            return None

        elif data['command'] == 'sign-in':
            if self.auth_status.get(client_id):
                return {'status': 'error', 'code': ' ALREADY_LOGGED_IN'}
            if data.get('username') is None:
                return {'status': 'error', 'code': 'NO_USERNAME'}
            if data.get('password') is None:
                return {'status': 'error', 'code': 'NO_PASSWORD'}
            this_user = self.database_session.query(User).filter(User.name == data['username']).first()
            self.database_session.flush()
            if not this_user:
                return {'status': 'error', 'code': 'NO_SUCH_USER'}
            if this_user.password == data['password']:
                self.auth_status[client_id] = _UserAuthenticationData(this_user.name, this_user.id)
                self.client_users[this_user.id] = client_id
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'code': 'WRONG_PASSWORD'}

        elif data['command'] == 'sign-out':
            if client_id in self.auth_status:
                del self.client_users[self.auth_status[client_id].uid]
                del self.auth_status[client_id]
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'code': 'NOT_SIGNED_IN'}

        elif data['command'] == 'get-status':
            if client_id in self.auth_status:
                user_data = self.auth_status[client_id]
                return {'status': 'ok', 'authenticated': True, 'username': user_data.username, 'id': user_data.uid}
            else:
                return {'status': 'ok', 'authenticated': False}

        elif data['command'] == 'sign-up':
            if 'username' not in data or data['username'] == '':
                return {'status': 'error', 'code': 'NO_USERNAME'}
            if 'password' not in data:
                return {'status': 'error', 'code': 'NO_PASSWORD'}
            if self.database_session.query(User).filter(User.name == data['username']).first():
                return {'status': 'error', 'code': 'LOGIN_TAKEN'}
            self.database_session.add(User(name=data['username'], password=data['password']))
            self.database_session.flush()
            return {'status': 'ok'}

        elif data['command'] == 'get-name':
            if 'id' not in data:
                return {'status': 'error', 'code': 'NO_ID'}
            this_user = self.database_session.query(User).filter(User.id == data['id']).first()
            if this_user:
                return {'status': 'ok', 'name': this_user.name}
            else:
                return {'status': 'error', 'code': 'NO_SUCH_USER'}

        return {'status': 'error', 'code': 'INVALID_COMMAND'}


class WaitingRoomManager:
    def __init__(self, server_manager : ServerManager):
        """
        Creates waiting room manager.
        :param server_manager: ServerManager using this class
        :return:
        """

        def query_handler(client_id, data):
            return self._query_handler(client_id, data)

        server = server_manager.server

        server.set_query_handler(4, query_handler)

        self.listeners = set()
        self.users = dict()
        self.server = server
        self.user_manager = server_manager.user_manager

    def _query_handler(self, client_id, data):
        """
        :param client_id: id of client sending query
        :param data: query to server
        :return: response to client
        """
        if 'command' not in data:
            return None

        elif data['command'] == 'start-listening':
            self.listeners.add(client_id)
            return {'status': 'ok'}

        elif data['command'] == 'stop-listening':
            if client_id not in self.listeners:
                return {'status': 'error', 'code': 'CLIENT_NOT_LISTENING'}
            self.listeners.discard(client_id)
            return {'status': 'ok'}

        elif data['command'] == 'get-status':
            if 'id' not in data:
                return {'status': 'error', 'code': 'NO_USERID'}
            elif data['id'] not in self.users:
                return {'status': 'ok', 'user-status': 'disconnected'}
            return {'status': 'ok', 'user-status': self.users[data['id']]}

        elif data['command'] == 'set-status':
            if 'new-status' not in data:
                return {'status': 'error', 'code': 'NO_NEW_STATUS'}
            user_id = self.user_manager.get_clients_user(client_id)
            if 'uid' in data and data['uid'] != user_id:
                return {'status': 'error', 'code': 'INVALID_USER'}
            if data['new-status'] == 'disconnected' and client_id in self.listeners:
                self.listeners.discard(client_id)
            for i in self.listeners:
                self.server.notify(i, 13, {'notification': 'status-change', 'user': user_id,
                                           'status': data['new-status']})
            if data['new-status'] == 'disconnected':
                del self.users[user_id]
            else:
                self.users[user_id] = data['new-status']
            return {'status': 'ok'}

        elif data['command'] == 'get-waiting-room':
            return {'status': 'ok', 'waiting-dict': self.users}

        return {'status': 'error', 'code': 'INVALID_COMMAND'}


class GameData:
    def __init__(self, player_1_client, player_2_client, game_board, game_board_2, game_pawn):
        """
        Creates information about game.
        :param player_1_client: nr of first client playing the game
        :param player_2_client: nr of second client playting the game
        :param game_board: 2 dimensional table with fields point values
        :param game_board_2: 2 dimensional table with game history
        :param game_pawn: 2 dimensional table with game pawn
        :return:
        """
        self.player_client = [0 for i in range(2)]
        self.player_client[0] = player_1_client
        self.player_client[1] = player_2_client
        self.game_board_point = game_board
        self.game_board_move = game_board_2
        self.game_pawn = game_pawn
        self.current_player = 1


class GameManager:
    def __init__(self, server, user_manager, db_session):
        """
        Creates game manager.
        :param server: server used to communication
        :param user_manager: part of server manager responsible for authentication
        :return:
        """

        def query_handler(client_id, data):
            return self._query_handler(client_id, data)

        server.set_query_handler(5, query_handler)

        self.server = server
        self.user_manager = user_manager
        self.random_one = None
        self.game_data = dict()
        self.counter = 0
        self.db_session = db_session

    def _check_move(self, x, y, board, pawn):
        """
        :param x: x coordinate of the move
        :param y: y coordinate of the move
        :param board: game history board on which the mobe would be performed
        :param pawn: pawn which would be used for the move
        :return: True if move is legal, False otherwise
        """
        for i in range(len(pawn)):
            for j in range(len(pawn[0])):
                try:
                    if pawn[x + i][y + j] == 1 and board[x][y] != 0:
                        return False
                except IndexError:
                    return False
        return True

    def _clockwised_pawn(self, pawn):
        """
        :param pawn: pawn to be rotated
        :return: rotated pawn
        """
        new_pawn = [[0 for i in range(len(pawn))] for j in range(len(pawn[0]))]
        for i in range(len(pawn)):
            for j in range(len(pawn[0])):
                if pawn[i][j] == 1:
                    new_pawn[j][len(pawn) - i - 1] = 1
        return new_pawn

    def _print_move(self, pawn, x, y, new_board, nr):
        """
        :param pawn: pawn to be printed on board
        :param x: x coordinate of the move
        :param y: y coordinate of the move
        :param new_board: board on which the move takes place
        :param nr: nr which should be printed
        :return:
        """
        for i in range(len(pawn)):
            for j in range(len(pawn[0])):
                if pawn[i][j] == 1:
                    new_board[x + i][y + j] = nr

    def _transform_after_move(self, pawn, move_board, nr):
        """
        :param pawn: pawn used for the game
        :param move_board: game history board
        :param nr: nr which should be printed on unreachable fields
        :return:
        """
        temp_pawn = pawn
        new_board = [[1 for j in range(len(move_board[0]))] for i in range(len(move_board))]
        for i in range(len(move_board)):
            for j in range(len(move_board[0])):
                if move_board[i][j] != 0:
                    new_board[i][j] = 0
        for k in range(4):
            temp_pawn = self._clockwised_pawn(temp_pawn)
            for i in range(len(move_board)):
                for j in range(len(move_board[0])):
                    if self._check_move(i, j, move_board, temp_pawn):
                        self._print_move(temp_pawn, i, j, new_board, 0)
        for i in range(len(move_board)):
            for j in range(len(move_board[0])):
                if new_board[i][j] == 1:
                    move_board[i][j] = nr

    def _start_random_game(self, game_number, player_1_client, player_2_client):
        """
        Puts information about game into game_data
        :param game_number: number of the game to be started
        :param player_1_client: first player playing game
        :param player_2_client: second player playing game
        :return:
        """
        game_pawns = self.db_session.query(GamePawn)
        random_game_pawn_raw = game_pawns.offset(int(int(game_pawns.count() * random.random()))).first()
        pawn_string = random_game_pawn_raw.shapestring
        pawn_table = [[0 for j in range(random_game_pawn_raw.height)] for i in range(random_game_pawn_raw.width)]
        for i in range(random_game_pawn_raw.width):
            for j in range(random_game_pawn_raw.height):
                if pawn_string[j * random_game_pawn_raw.width + i] == '1':
                    pawn_table[i][j] = 1
        game_boards = self.db_session.query(GameBoard)
        random_game_board_raw = game_boards.offset(int(int(game_boards.count() * random.random()))).first()
        game_string = random_game_board_raw.shapestring
        board_table2 = [[-3 for j in range(random_game_board_raw.height)] for i in range(random_game_board_raw.width)]
        for i in range(random_game_board_raw.width):
            for j in range(random_game_board_raw.height):
                if game_string[j * random_game_board_raw.width + i] == '1':
                    board_table2[i][j] = 0
        self._transform_after_move(pawn_table, board_table2, -3)
        board_table = [[0 for j in range(random_game_board_raw.height)] for i in range(random_game_board_raw.width)]
        for i in range(random_game_board_raw.width):
            for j in range(random_game_board_raw.height):
                if board_table2[i][j] == '0':
                    board_table[i][j] = random.randint(1, 9)

        self.game_data[game_number] = GameData(player_1_client, player_2_client, board_table, board_table2,
                                               pawn_table)

    def _query_handler(self, client_id, data):
        """
        :param client_id: id of client sending query
        :param data: query content
        :return: response to client
        """
        if 'command' not in data:
            return None
        elif data['command'] == 'find-random-game':
            if self.random_one is not None:
                self.counter += 1
                self._start_random_game(self.counter, self.random_one, client_id)
                self.server.notify(self.random_one, 14, {'notification': 'opponent-found',
                                                         'opponent-id': self.user_manager.get_clients_user(client_id),
                                                         'game-nr': self.counter, 'player-number': 1,
                                                         'game-board': self.game_data[self.counter].game_board_point,
                                                         'game-pawn': self.game_data[self.counter].game_pawn})
                return_value = {'status': 'ok', 'game-status': 'found',
                                'opponent-id': self.user_manager.get_clients_user(self.random_one),
                                'game-nr': self.counter, 'player-number': 2,
                                'game-board': self.game_data[self.counter].game_board_point,
                                'game-pawn': self.game_data[self.counter].game_pawn}
                self.random_one = None
                return return_value
            else:
                self.random_one = client_id
                return {'status': 'ok', 'game-status': 'waiting'}
        elif data['command'] == 'abandon-game':
            if 'game-nr' not in data:
                return {'status': 'error', 'code': 'NO_GAME_NR'}
            elif data['game-nr'] not in self.game_data:
                return {'status': 'error', 'code': 'BAD_GAME_NR'}
            elif 'player-nr' not in data:
                return {'status': 'error', 'code': 'NO_PLAYER'}
            elif self.game_data[data['game-nr']].player_client[data['player-nr'] - 1] != client_id:
                return {'status': 'error', 'code': 'BAD_GAME_PLAYER_NR'}
            self.server.notify(self.game_data[data['game-nr']].player_client[2 - data['player-nr']], 15,
                               {'notification': 'game-finished', 'result': 'won', 'detail': 'enemy-abandoned-game',
                                'game-nr': data['game-nr']})
            del self.game_data[data['game-nr']]
            return {'status': 'ok', 'game-result': 'defeated', 'detail': 'game-abandoned'}
        elif data['command'] == 'quit-searching':
            if client_id != self.random_one:
                return {'status': 'error', 'code': 'NOT_SEARCHING'}
            self.random_one = None
            return {'status': 'ok'}
        elif data['command'] == 'move':
            if 'game-nr' not in data:
                return {'status': 'error', 'code': 'NO_GAME_NR'}
            elif data['game-nr'] not in self.game_data:
                return {'status': 'error', 'code': 'BAD_GAME_NR'}
            elif 'player-nr' not in data:
                return {'status': 'error', 'code': 'NO_PLAYER'}
            elif self.game_data[data['game-nr']].player_client[data['player-nr'] - 1] != client_id:
                return {'status': 'error', 'code': 'BAD_GAME_PLAYER_NR'}
            elif data['player-nr'] != self.game_data[data['game-nr']].current_player:
                return {'status': 'error', 'code': 'WRONG_TURN'}
            elif 'x' not in data or 'y' not in data or 'rotation' not in data:
                return {'status': 'error', 'code': 'NO_MOVE'}
            temp_pawn = self.game_data[data['game-nr']].game_pawn
            for i in range(data['rotation']):
                temp_pawn = self._clockwised_pawn(temp_pawn)
            if not self._check_move(data['x'], data['y'], self.game_data[data['game-nr']].game_board_move, temp_pawn):
                return {'status': 'error', 'code': 'WRONG_MOVE'}
            self.game_data[data['game-nr']].current_player = 3 - data['player-nr']
            self._print_move(temp_pawn, data['x'], data['y'], self.game_data[data['game-nr']].moveboard,
                             data['player-nr'])
            self._transform_after_move(temp_pawn, self.game_data[data['game-nr']].game_board_move, -data['player-nr'])
            player_1_score = 0
            player_2_score = 0
            is_it_end = True
            for i in range(len(self.game_data[data['game-nr']].game_board_move)):
                for j in range(len(self.game_data[data['game-nr']].game_board_move[0])):
                    if self.game_data[data['game-nr']].game_board_move[i][j] == 0:
                        is_it_end = False
                    elif self.game_data[data['game-nr']].game_board_move[i][j] == -1:
                        player_1_score += self.game_data[data['game-nr']].game_board_point[i][j]
                    elif self.game_data[data['game-nr']].game_board_move[i][j] == -2:
                        player_2_score += self.game_data[data['game-nr']].game_board_point[i][j]
            if is_it_end:
                if player_1_score > player_2_score:
                    self.server.notify(self.game_data[data['game-nr']].player_client[2 - data['player-nr']], 15,
                                       {'notification': 'game-finished', 'winner': 1, 'detail': 'no-more-moves',
                                        'game-nr': data['game-nr'], 'game_move_board': self.game_data[data['game-nr']].game_board_move,
                                        'player_1_points': player_1_score, 'player_2_points': player_2_score})

                    to_return = {'status': 'ok', 'game-status': 'finished', 'winner': 1, 'detail': 'no-more-moves',
                            'game-nr': data['game-nr'],
                            'game_move_board': self.game_data[data['game-nr']].game_board_move,
                            'player_1_points': player_1_score, 'player_2_points': player_2_score}
                    del self.game_data[data['game-nr']]
                    return to_return
                elif player_2_score > player_1_score:
                    self.server.notify(self.game_data[data['game-nr']].player_client[2 - data['player-nr']], 15,
                                       {'notification': 'game-finished', 'winner': 2, 'detail': 'no-more-moves',
                                        'game-nr': data['game-nr'],
                                        'game_move_board': self.game_data[data['game-nr']].game_board_move,
                                        'player_1_points': player_1_score, 'player_2_points': player_2_score})
                    to_return = {'status': 'ok', 'game-status': 'finished', 'winner': 2, 'detail': 'no-more-moves',
                            'game-nr': data['game-nr'], 'game_move_board': self.game_data[data['game-nr']].game_board_move,
                            'player_1_points': player_1_score, 'player_2_points': player_2_score}
                    del self.game_data[data['game-nr']]
                    return to_return
                else:
                    self.server.notify(self.game_data[data['game-nr']].player_client[2 - data['player-nr']], 15,
                                       {'notification': 'game-finished', 'winner': 0, 'detail': 'no-more-moves',
                                        'game-nr': data['game-nr']})
                    to_return = {'status': 'ok', 'game-status': 'finished', 'winner': 0, 'detail': 'no-more-moves',
                            'game-nr': data['game-nr'], 'game_move_board': self.game_data[data['game-nr']].game_board_move,
                                                         'player_1_points': player_1_score, 'player_2_points': player_2_score}
                    del self.game_data[data['game-nr']]
                    return to_return
            self.server.notify(self.game_data[data['game-nr']].player_client[2 - data['player-nr']], 15,
                               {'notification': 'your-new-turn',
                                'game-nr': data['game-nr'],
                                'game_move_board': self.game_data[data['game-nr']].game_board_move,
                                'player_1_points': player_1_score, 'player_2_points': player_2_score})
            return {'status': 'ok', 'game-status': 'opponents-turn', 'game_move_board': self.game_data[data['game-nr']].game_board_move,
                    'player_1_points': player_1_score, 'player_2_points': player_2_score}

        return {'status': 'error', 'code': 'INVALID_COMMAND'}


def main():
    arg_parser = argparse.ArgumentParser(description="DVD Yellow Project server")
    arg_parser.add_argument('--config', metavar='file', dest='config_file', type=str, default=None,
                            help="Server configuration file")

    args = arg_parser.parse_args()

    server_manager = ServerManager(config_file=args.config_file)
    server_manager.run()


if __name__ == '__main__':
    main()
