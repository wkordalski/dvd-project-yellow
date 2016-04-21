import threading
from random import Random, randint
from threading import Thread
from time import sleep
from unittest.case import TestCase

from dvdyellow.game import make_session
from dvdyellow.orm import User
from dvdyellow.server import ServerManager


class AuthenticationTests(TestCase):
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
            sleep(0.01)
        sleep(0.1)

    def tearDown(self):
        self.server_manager.stop()
        self.server_thread.join(timeout=3.)

    def test_sign_in(self):
        """
        Tries to sign in to an existing account.
        """
        session = make_session('localhost', self.port).result
        session.sign_in('john', 'best123')
        self.assertIsNotNone(session.get_signed_in_user().result, "User haven't logged in.")
        session.sign_out()

    def test_sign_in_empty_password(self):
        """
        Tries to sign in to an existing account.
        """
        session = make_session('localhost', self.port).result
        session.sign_in('lazy', '')
        self.assertIsNotNone(session.get_signed_in_user().result, "User haven't logged in.")
        session.sign_out()

    def test_sign_in_wrong_username(self):
        """
        Tries to sign in to a not existing account.
        """
        session = make_session('localhost', self.port).result
        session.sign_in('johnny', 'best123')
        self.assertIsNone(session.get_signed_in_user().result, "User have logged in.")

    def test_sign_in_wrong_password(self):
        """
        Tries to sign in with correct username and wrong password.
        """
        session = make_session('localhost', self.port).result
        session.sign_in('john', 'wrong_password')
        self.assertIsNone(session.get_signed_in_user().result, "User have logged in.")

    def test_sign_up(self):
        """
        Tries to sign up with correct username.
        """
        session = make_session('localhost', self.port).result
        self.assertTrue(session.sign_up('me', 'good_password').result, "Signing up failed")
        session.sign_in('me', 'good_password')
        self.assertIsNotNone(session.get_signed_in_user().result, "User haven't logged in.")
        session.sign_out()

    def test_sign_up_used_username(self):
        """
        Tries to sign up with used username.
        """
        session = make_session('localhost', self.port).result
        self.assertFalse(session.sign_up('john', 'good_password').result, "Signing up succeeded")

    def test_sign_up_empty_password(self):
        """
        Tries to sign up with empty password (should pass)
        """
        session = make_session('localhost', self.port).result
        self.assertTrue(session.sign_up('me', '').result, "Signing up failed")
        session.sign_in('me', '')
        self.assertIsNotNone(session.get_signed_in_user().result, "User haven't logged in.")
        session.sign_out()

    def test_sign_up_empty_username(self):
        """
        Tries to sign up with empty username (should not pass)
        """
        session = make_session('localhost', self.port).result
        self.assertFalse(session.sign_up('', 'good_password').result, "Signing up succeeded.")

