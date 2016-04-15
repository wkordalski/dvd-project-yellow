from unittest.case import TestCase
from threading import Thread

from sfml.system import sleep, milliseconds

from dvdyellow.network import *


class NetworkTests(TestCase):
    def _connect_loop(self, connector, seconds):
        for i in range(int(seconds * 10)):
            if connector.is_connected: break
            sleep(milliseconds(100))

    def test_connect(self):
        server = Server(lambda x: True)
        client = Client(123)
        srv_th = Thread(target=Server.listen, args=(server, '127.0.0.1', 1236))
        srv_th.start()

        def stop_network(timeout):
            client.disconnect()
            server.close()
            srv_th.join(timeout=timeout)

        c = client.connect('127.0.0.1', 1236)
        self._connect_loop(c, 3.)
        try:
            self.assertTrue(c.is_connected)
        except AssertionError:
            stop_network(2.)
            raise

        stop_network(2.)
        self.assertFalse(srv_th.is_alive())

    def test_query(self):
        server = Server(lambda x: x == 1)
        # some echo module ;-)
        server.set_query_handler(7, lambda cid, msg: msg)
        client = Client(1)
        srv_th = Thread(target=Server.listen, args=(server, '127.0.0.1', 1235))
        srv_th.start()

        def stop_network(timeout):
            client.disconnect()
            server.close()
            srv_th.join(timeout=timeout)

        c = client.connect('127.0.0.1', 1235)
        self._connect_loop(c, 3.)
        try:
            self.assertTrue(c.is_connected)
        except AssertionError:
            stop_network(2.)
            raise

        data = {'name': 'ASD'}
        r = client.query(7, data)
        obj = r.response
        try:
            self.assertDictEqual(obj, data)
        except AssertionError:
            stop_network(2.)
            raise

        stop_network(2.)
        self.assertFalse(srv_th.is_alive())

    def test_notifications(self):
        """
        Server is notificating everybody about other client entrances on channel 12.
        """
        server = Server(lambda x: x == 1)

        def on_new_client(client_id):
            # notify other clients
            for cid in server.clients.keys():
                if cid == client_id: continue
                server.notify(cid, 12, {'new-client': client_id})

        server.set_accept_handler(on_new_client)

        consumer = Client(1)    # client wanting notification
        producer = Client(1)    # client making notification sending

        srv_th = Thread(target=Server.listen, args=(server, '127.0.0.1', 1234))
        srv_th.start()

        def stop_network(timeout):
            consumer.disconnect()
            producer.disconnect()
            server.close()
            srv_th.join(timeout=timeout)

        # setup consumer
        got_notification = False

        def on_notification(channel, data):
            if channel == 12 and 'new-client' in data:
                nonlocal got_notification
                got_notification = True
        consumer.set_notification_handler(12, on_notification)

        # connect consumer
        c = consumer.connect('127.0.0.1', 1234)
        self._connect_loop(c, 3.)
        try:
            self.assertTrue(c.is_connected)
        except AssertionError:
            stop_network(2.)
            raise

        # connected, so connect producer
        c = producer.connect('127.0.0.1', 1234)
        self._connect_loop(c, 3.)
        try:
            self.assertTrue(c.is_connected)
        except AssertionError:
            stop_network(2.)
            raise

        # we should get the notification right now
        for i in range(30):
            consumer.receive_all()
            if got_notification: break
            sleep(milliseconds(100))

        try:
            self.assertTrue(got_notification)
        except AssertionError:
            stop_network(2.)
            raise

        stop_network(2.)
        self.assertFalse(srv_th.is_alive())
