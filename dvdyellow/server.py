"""
Server manager and server modules will be implemented here.
"""
import logging
import os

import yaml
from functools import reduce

import random
from appdirs import AppDirs
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm.session import sessionmaker

from dvdyellow.orm import create_schemes
from .orm import User, GameBoard, GamePawn
from .network import Server


class ServerManager:
    def __init__(self, target_configuration=None, config_file=None, config_object=None):
        self.server = Server(lambda x: x == 1)
        self.logger = logging.getLogger("ServerManager")
        self.dirs = AppDirs('dvdyellow', appauthor='yellow-team', multipath=True)

        self._setup_server_configuration(target_configuration, config_file, config_object)
        self._setup_database()

        self.user_manager = UserManager(self.server, self.db_session)
        self.waiting_room = WaitingRoomManager(self.server)
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
        self.server.listen('0.0.0.0', self.port)

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
        :param server:
        :param db_session:
        :return:
        """
        def permission_checker(client_id, module):
            return self._permission_checker(client_id, module)

        def query_handler(client_id, data):
            return self._query_handler(client_id, data)

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

    def get_users_client(self, user_id):
        return self.client_users.get(user_id)

    def get_clients_user(self, client_id):
        return self.auth_status[client_id].uid

    def _query_handler(self, client_id, data):
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
            if 'username' not in data:
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
                return {'status':'error', 'code': 'NO_ID'}
            this_user = self.database_session.query(User).filter(User.id == data['id']).first()
            if this_user:
                return {'status': 'ok', 'name': this_user.name}
            else:
                return {'status': 'error', 'code': 'NO_SUCH_USER'}

        return {'status': 'error', 'code': 'INVALID_COMMAND'}


class WaitingRoomManager:
    def __init__(self, server):
        """
        Creates waiting room manager.
        :param server:
        :return:
        """
        def query_handler(client_id, data):
            self._query_handler(client_id, data)

        server.set_query_handler(4, query_handler)
        
        self.listeners = set()
        self.users = dict()
        self.server = server
        
    def _query_handler(self, client_id, data):
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
            if 'name' not in data:
                return {'status': 'error', 'code': 'NO_USERNAME'}
            if 'id' not in data:
                return {'status': 'error', 'code': 'NO_USER_ID'}
            if data['new-status'] == 'disconnected' and client_id in self.listeners:
                self.listeners.discard(client_id)
            for i in self.listeners:
                self.server.notify(i, 13, {'notification': 'status-change', 'user': data['name'],
                                           'id': data['id'], 'status': data['new-status']})
            if data['new-status'] == 'disconnected':
                del self.users[data['id']]
            else:
                self.users[data['id']] = data['new-status']
            return {'status': 'ok'}

        elif data['command'] == 'get-waiting-room':
            return {'status': 'ok', 'waiting-dict': self.users}

        return {'status': 'error', 'code': 'INVALID_COMMAND'}

class GameData:
    def __init__(self, number, player_1_client, player_2_client, gameboard, gameboard2, gamepawn):
        """
        Creates information about game.
        :param number:
        :param player_1_client:
        :param player_2_client:
        :param gameboard:
        :param gameboard2:
        :param gamepawn:
        :return:
        """
        self.player_1_client = player_1_client
        self.player_2_client = player_2_client
        self.game_board_point = gameboard
        self.game_board_move = gameboard2
        self.game_pawn = gamepawn
        self.current_player = 1


class GameManager:
    def __init__(self, server, usermanager, db_session):
        """
        Creates game manager.
        :param server:
        :param usermanager:
        :return:
        """
        def query_handler(client_id, data):
            self._query_handler(client_id, data)

        server.set_query_handler(5, query_handler)

        self.server = server
        self.usermanager = usermanager
        self.random_one = None
        self.game_data = dict()
        self.counter = 0
        self.db_session = db_session

    def _check_move(self, y, x, board, pawn):
        for i in range(len(pawn)):
            for j in range(len(pawn[0])):
                try:
                    if pawn[y + i][x + j] == 1 and board [y][x] < 0:
                        return False
                except IndexError:
                    return False
        return True

    def _swapped_pawn(self, pawn):
        newpawn = reversed(pawn)
        return newpawn

    def _clockwised_pawn(self, pawn):
        newpawn = [[0 for i in range(len(pawn))] for j in range(len(pawn[0]))]
        for i in range(len(pawn)):
            for j in range(len(pawn[0])):
                newpawn[j][len(pawn) ] = pawn[i][j]
        return newpawn


    def _start_random_game(self, game_number, player_1_client, player_2_client):
        gameboards = self.db_session.query(GameBoard)
        random_gameboard_raw = gameboards.offset(int(int(gameboards.count() * random.random()))).first()
        game_string = random_gameboard_raw.shapestring
        board_table = [[0 for j in range(random_gameboard_raw.height)] for i in range(random_gameboard_raw.width)]
        for i in range(random_gameboard_raw.width):
            for j in range(random_gameboard_raw.height):
                if game_string[j * random_gameboard_raw.height + i] == '1':
                    board_table[i][j] = random.randint(1,9)
        board_table2 = [[-3 for j in range(random_gameboard_raw.height)] for i in range(random_gameboard_raw.width)]
        for i in range(random_gameboard_raw.width):
            for j in range(random_gameboard_raw.height):
                if game_string[j * random_gameboard_raw.height + i] == '1':
                    board_table2[i][j] = 0
        gamepawns = self.db_session.query(GamePawn)
        random_gamepawn_raw = gamepawns.offset(int(int(gamepawns.count() * random.random()))).first()
        pawn_string = random_gamepawn_raw.shapestring
        pawn_table = [[0 for j in range(random_gamepawn_raw.height)] for i in range(random_gamepawn_raw.width)]
        for i in range(random_gamepawn_raw.width):
            for j in range(random_gamepawn_raw.height):
                if pawn_string[j * random_gameboard_raw.height + i] == '1':
                    pawn_table[i][j] = 1
        #TODO: check if it's possible to cover field
        self.game_data[game_number] = GameData(game_number, player_1_client,player_2_client, board_table, board_table2,
                                               pawn_table)


    def _query_handler(self, client_id, data):
        if 'command' not in data:
            return None
        elif data['command'] == 'find-random-game':
            if self.random_one is not None:
                self.counter = self.counter + 1
                self._start_random_game(self.counter, self.random_one, client_id)
                self.server.notify(self.random_one, 14, {'notification': 'opponent-found', 'opponent-id': self.usermanager.get_clients_user(client_id),
                                                         'game-nr': self.counter, 'player-number': 1,
                                                         'game_board': self.game_data[self.counter].game_board_point,
                                                         'game-pawn': self.game_data[self.counter].game_pawn})
                return_value = {'status': 'ok', 'game-status': 'found', 'opponent-id': self.usermanager.get_users_client(self.random_one),
                                'game-nr': self.counter, 'player-number': 2}
                self.random_one = None
                return return_value
            else:
                random_one = client_id
                return {'status': 'ok', 'game-status':'waiting'}
        elif data['command'] == 'abandon-game':
            pass
        elif data['command'] == 'finish-turn':
            pass


        return {'status': 'error', 'code': 'INVALID_COMMAND'}