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

from dvdyellow.orm import Database
from .network import Server


class ServerManager:
    def __init__(self, target_configuration='local', config_file=None, config_object=None):
        self.server = Server(lambda x: x == 1)
        self.logger = logging.getLogger("ServerManager")
        self.dirs = AppDirs('dvdyellow', appauthor='yellow-team', multipath=True)

        self._setup_server_configuration(target_configuration, config_file, config_object)
        self._setup_database()

        self.user_manager = UserManager(self.server)

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
            if not os.path.isfile(conf_file): continue
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
            elts = getter.split('.')
            getter = lambda c: reduce(lambda d, k: d[k], elts, c)

        for config in self.configurations:
            if not config: continue
            try:
                r = getter(config)
                if r == '' and is_empty_default:
                    return default
                else:
                    return r
            except KeyError:
                pass

        return default

    def _setup_server_configuration(self, target_configuration='local', config_file=None, config_object=None):
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

        target_cfg = self.config[target_configuration] if self.config and target_configuration in self.config else None
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
