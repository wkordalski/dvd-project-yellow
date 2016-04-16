"""
Server manager and server modules will be implemented here.
"""
import logging
import os
import yaml
from functools import reduce

from appdirs import AppDirs
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm.session import sessionmaker

from .orm import Database, User
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
        
    def _load_config_file(self, path):
        try:
            f = open(path)
            self.config = yaml.safe_load(f)
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
        Database.metadata.create_all(self.db)

        self.db_session = sessionmaker(bind=self.db)

    def run(self):
        """
        Runs server.
        """
        self.server.listen('0.0.0.0', self.port)


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

    def _permission_checker(self, client_id, module):
        if module == 3:
            return True

        if client_id in self.auth_status:
            return True
            
        return False

    def _query_handler(self, client_id, data):
        if 'command' not in data:
            return None

        if data['command'] == 'sign-in':
            if self.auth_status[client_id]:
                return {'status': 'error', 'code': ' ALREADY_LOGGED_IN'}
            if not data['name']:
                return {'status': 'error', 'code': 'NO_USERNAME'}
            if not data['password']:
                return {'status': 'error', 'code': 'NO_PASSWORD'}
            this_user = self.database_session.query(User).filter(name=data['name']).first()
            if not this_user:
                return {'status': 'error', 'code': 'NO_SUCH_USER'}
            if this_user.password == data['password']:
                self.auth_status[client_id] = _UserAuthenticationData(this_user.name, this_user.id)
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
            if not data['name']:
                return {'status': 'error', 'code': 'NO_USERNAME'}
            if not data['password']:
                return {'status': 'error', 'code': 'NO_PASSWORD'}
            if self.database_session.query(User).filter(name=data['name']).first():
                return {'status': 'error', 'code': 'LOGIN_TAKEN'}
            self.database_session.User.insert().values({'name': data['name'], 'password': data['password']})
            self.database_session.flush()
            return {'status': 'ok'}

        return {'status': 'error', 'code': 'INVALID_COMMAND'}


class WaitingRoomManager:
    def __init__(self, server):
        """
        Creates user manager.
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
        
        if data['command'] == 'start-listening':
            self.listeners.add(client_id)
            return {'status': 'ok'}
        
        elif data['command'] == 'stop-listening':
            if client_id not in self.listeners:
                return {'status': 'error', 'code': 'CLIENT_NOT_LISTENING'}
            self.listeners.discard(client_id)
            return {'status': 'ok'}
        
        elif data['command'] == 'check-status':
            if not data['username']:
                return {'status': 'error', 'code': 'NO_USERNAME'}
            elif data['username'] not in self.users:
                return {'status': 'ok', 'user-status': 'disconnected'}
            return {'status': 'ok', 'user-status': self.users[data['username']]}
         
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
                del self.users[client_id]
            else:
                self.users[client_id] = data['new-status']
            return {'status': 'ok'}
            
        return {'status': 'error', 'code': 'INVALID_COMMAND'}
