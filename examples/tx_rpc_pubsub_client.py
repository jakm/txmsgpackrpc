from __future__ import print_function
import os

from twisted.internet import defer, reactor

def on_publish(topic, params):
    print(str(params))

c = None

@defer.inlineCallbacks
def main():
    try:

        from txmsgpackrpc.client import connect

        c = yield connect('localhost', 8000, connectTimeout=5)

        res = yield c.createSubscribe('notification', on_publish)
        assert 0 == res

        data = (str(os.getpid()))
        res = yield c.createRequest('echo', data)
        assert data == res

        """
        d = defer.Deferred()
        reactor.callLater(30, d.callback, None)
        res = yield d

        res = yield c.createUnsubscribe('notification')
        assert 0 == res
        """


    except Exception:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
