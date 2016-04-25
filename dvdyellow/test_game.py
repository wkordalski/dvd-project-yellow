import threading
from random import Random, randint
from threading import Thread
from sfml import sleep, milliseconds
from unittest.case import TestCase

from dvdyellow.game import make_session
from dvdyellow.orm import User, GameBoard, GamePawn
from dvdyellow.server import ServerManager


class GameTests(TestCase):
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
            dbs.add(GamePawn(name='test_pawn', width=2, height=3, shapestring="100110"))
            dbs.add(GameBoard(name='test_board', width=6, height=8, shapestring="0"*48))
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

    def test_user_into_games_pairing(self):
        """
        Two users wants to play a game and should be paired.
        """
        session1 = make_session('localhost', self.port).result
        session1.sign_in('john', 'best123').result

        session2 = make_session('localhost', self.port).result
        session2.sign_in('lazy', '').result

        game1 = None

        def game_found(game):
            nonlocal game1
            game1 = game

        session1.on_game_found = game_found

        r = session1.set_want_to_play()
        self.assertIsNone(r.result)

        r = session2.set_want_to_play()
        game2 = r.result

        session1.process_events()
        session2.process_events()

        self.assertIsNotNone(game1)
        self.assertIsNotNone(game2)
        self.assertEqual(game1.gid, game2.gid)

        session1.del_waiting_room().result
        session1.sign_out().result

        session2.process_events()

        session2.del_waiting_room().result
        session2.sign_out().result

    def test_user_want_to_play_cancellation(self):
        """
        Two users wants to play a game but the first one cancels it request.
        """
        session1 = make_session('localhost', self.port).result
        session1.sign_in('john', 'best123').result

        session2 = make_session('localhost', self.port).result
        session2.sign_in('lazy', '').result

        game1 = None

        def game_found(game):
            nonlocal game1
            game1 = game

        session1.on_game_found = game_found

        r = session1.set_want_to_play()
        self.assertIsNone(r.result)

        r = session1.cancel_want_to_play()
        self.assertTrue(r.result)

        r = session2.set_want_to_play()
        game2 = r.result

        session1.process_events()
        session2.process_events()

        self.assertIsNone(game1)
        self.assertIsNone(game2)

        session1.del_waiting_room().result
        session1.sign_out().result

        session2.process_events()

        session2.del_waiting_room().result
        session2.sign_out().result