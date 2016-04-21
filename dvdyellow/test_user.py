import threading
from random import Random, randint
from threading import Thread
from time import sleep
from unittest.case import TestCase

from dvdyellow.game import make_session
from dvdyellow.orm import User
from dvdyellow.server import ServerManager


class UserTests(TestCase):
    def setUp(self):
        self.port = randint(10000, 65000)
        self.server_manager = None
        self.server_started = False

        def server_thread(test_case):
            test_case.server_manager = ServerManager(config_object={'network':{'port': self.port}})

            def on_run():
                test_case.server_started = True
            test_case.server_manager.on_run = on_run

            dbs = test_case.server_manager.db_session_type()
            dbs.add(User(name='john', password='best123'))
            dbs.flush()
            test_case.server_manager.run()

        self.server_thread = Thread(target=server_thread, args=(self,))
        self.server_thread.start()

        while not self.server_started:
            sleep(0.01)
        sleep(0.1)

    def tearDown(self):
        self.server_manager.stop()
        self.server_thread.join(timeout=3.)

    def test_user_get_name(self):
        """
        Tries to check the name of user.
        """
        session = make_session('localhost', self.port).result
        session.sign_in('john', 'best123')
        user = session.get_signed_in_user().result
        self.assertIsNotNone(user, "User haven't logged in.")
        self.assertEqual(user.name.result, 'john')
        session.sign_out()
