import time
from multiprocessing import Process

from twisted.internet import defer, reactor, error
from twisted.trial import unittest

import txmsgpackrpc
from txmsgpackrpc.server import MsgpackRPCServer
from txmsgpackrpc.client import connect


HOST = 'localhost'
PORT = 8899



class FakeServer(MsgpackRPCServer):
    def __init__(self):
        pass

    def remote_wait(self, timeout):
        time.sleep(timeout)
        return defer.succeed('I am too slow')

    def remote_fail(self):
        return defer.fail(RuntimeError)


    def remote_ok(self):
        return defer.succeed('Hi guy')



def run_server(host, port):
    reactor.listenTCP(port, FakeServer().getStreamFactory())
    reactor.callLater(10, reactor.stop)
    reactor.run()



class ClientTest(unittest.TestCase):
    @defer.inlineCallbacks
    def setUp(self):
        self.server = Process(target=run_server, args=(HOST, PORT))
        self.server.start()
        self.tested_proxy = yield connect(HOST, PORT, connectTimeout=None, waitTimeout=None)


    @defer.inlineCallbacks
    def tearDown(self):
        yield self.tested_proxy.disconnect()
        self.server.terminate()


    @defer.inlineCallbacks
    def test_okRequest(self):
        """
        Test request returning callback
        """
        real = yield self.tested_proxy.createRequest('ok')
        self.assertEqual(real, 'Hi guy')


    def test_failingRequest(self):
        """
        Test request returning errback
        """
        real = self.tested_proxy.createRequest('fail')
        return self.assertFailure(real, txmsgpackrpc.error.ResponseError)


    def test_lostConnection(self):
        """
        Test request with connection lost on server side
        """
        d = self.tested_proxy.createRequest('wait', 3)
        self.server.terminate()
        return self.assertFailure(d, error.ConnectionDone)


    def test_lostClientConnection(self):
        """
        When stopping factory after done some request, the exception from handler.py:81 is raised.
        But the failed deferred must be returned not a synchronous exception raised
        """
        def callback(data):
            self.tested_proxy.factory.doStop()
            self.tested_proxy.disconnect()
            d = self.tested_proxy.createRequest('ok')
            return self.assertFailure(d, txmsgpackrpc.error.ConnectionError)

        d1 = self.tested_proxy.createRequest('ok')
        d1.addBoth(callback)
