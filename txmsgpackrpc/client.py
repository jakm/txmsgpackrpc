from twisted.internet import reactor

from txmsgpackrpc.factory import MsgpackClientFactory
from txmsgpackrpc.handler import PooledConnectionHandler


def connect(host, port, connectTimeout=None, waitTimeout=None, maxRetries=5):
    factory = MsgpackClientFactory(connectTimeout=connectTimeout,
                                   waitTimeout=waitTimeout)
    factory.maxRetries = maxRetries

    reactor.connectTCP(host, port, factory, timeout=connectTimeout)

    d = factory.handler.waitForConnection()
    d.addCallback(lambda conn: factory.handler)

    return d


def connect_pool(host, port, poolsize=10, isolated=False,
                 connectTimeout=None, waitTimeout=None, maxRetries=5):
    factory = MsgpackClientFactory(handler=PooledConnectionHandler,
                                   handlerConfig={'poolsize': poolsize,
                                                  'isolated': isolated},
                                   connectTimeout=connectTimeout,
                                   waitTimeout=waitTimeout)
    factory.maxRetries = maxRetries

    for _ in range(poolsize):
        reactor.connectTCP(host, port, factory, timeout=connectTimeout)

    d = factory.handler.waitForConnection()
    d.addCallback(lambda conn: factory.handler)

    return d


__all__ = ['connect', 'connect_pool']
