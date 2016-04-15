"""
Server manager and server modules will be implemented here.
"""
import logging
import os
import yaml
from functools import reduce

from appdirs import AppDirs
from .network import Server


class ServerManager:
    def __init__(self, target_configuration='local', config_file=None):
        self.server = Server(lambda x: x == 1)
        self.logger = logging.getLogger("ServerManager")

        dirs = AppDirs('dvdyellow', appauthor='yellow-team', multipath=True)

        # read config
        self.config = None
        if not config_file:
            config_paths = filter(None, dirs.user_config_dir.split(os.pathsep) + dirs.site_config_dir.split(os.pathsep))
            self._load_configuration(config_paths)
        else:
            self._load_config_file(config_file)



        target_cfg = self.config[target_configuration] if target_configuration in self.config else None
        default_cfg = self.config['default'] if 'default' in self.config else None

        # possible configurations - first is most important
        self.configurations = list(filter(None, [target_cfg, default_cfg]))

        self._setup_server_configuration()

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

    def _get_config_entry(self, getter, default):
        """
        Returns entry value from configuration.
        :param getter: Function getting value from configuration object or string with dot-separated ids.
        :param default: Default values if nowhere such entry is present.
        :return: The value of such entry.
        """
        if isinstance(getter, str):
            elts = getter.split('.')
            getter = lambda c: reduce(lambda d, k: d[k], elts, c)

        for config in configurations:
            if not config: continue
            try:
                return getter(config)
            except KeyError:
                pass

        return default

    def _setup_server_configuration(self):
        #
        # NETWORK SETTINGS
        #
        self.port = self._get_config_entry('network.port', 42371)

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
