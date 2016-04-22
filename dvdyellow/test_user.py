import threading
from random import Random, randint
from threading import Thread
from sfml import sleep, milliseconds
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
            dbs.add(User(name='lazy', password=''))
            dbs.flush()
            test_case.server_manager.run()

        self.server_thread = Thread(target=server_thread, args=(self,))
        self.server_thread.start()

        while not self.server_started:
            sleep(milliseconds(10))
        sleep(milliseconds(100))

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

    def test_user_get_status(self):
        """
        Check if signed in user has status 'connected'
        """
        session = make_session('localhost', self.port).result
        session.sign_in('john', 'best123').result
        user = session.get_signed_in_user().result
        self.assertEqual(user.get_status().result, 'connected')
        session.sign_out()

    def test_user_status_monitoring(self):
        """
        Check if status is correctly stored.
        """
        session = make_session('localhost', self.port).result
        session.sign_in('john', 'best123').result
        session.get_waiting_room().result
        user = session.get_signed_in_user().result

        session2 = make_session('localhost', self.port).result
        session2.sign_in('lazy', '').result
        users = session2.get_waiting_room().result.get_online_users().result
        self.assertEqual(len(users), 2)

        user_names = ['john', 'lazy']
        john = None
        for u in users:
            if u.id == user.id:
                john = u

            if u.name.result not in user_names:
                user_names.remove(u.name)
                self.assertTrue(False, "Unknown user")

        self.assertEqual(john.get_status().result, 'connected')

        user.set_status('coding').result

        session2.process_events()

        self.assertEqual(john.get_status().result, 'coding')

        session.del_waiting_room().result
        session.sign_out().result

        session2.process_events()
        self.assertEqual(john.get_status().result, 'disconnected')

        session2.del_waiting_room().result
        session2.sign_out().result
