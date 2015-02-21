import sys

from twisted.internet import reactor

from txmsgpackrpc.factory import MsgpackClientFactory
from txmsgpackrpc.handler import PooledConnectionHandler


def __connect(host, port, factory, connectTimeout, ssl, ssl_CertificateOptions):
    if not ssl:
        reactor.connectTCP(host, port, factory, timeout=connectTimeout)
    else:
        if not ssl_CertificateOptions:
            from twisted.internet import ssl
            ssl_CertificateOptions = ssl.CertificateOptions()
        reactor.connectSSL(host, port, factory, ssl_CertificateOptions, timeout=connectTimeout)


def connect(host, port, connectTimeout=None, waitTimeout=None, maxRetries=5,
            ssl=False, ssl_CertificateOptions=None):
    factory = MsgpackClientFactory(connectTimeout=connectTimeout,
                                   waitTimeout=waitTimeout)
    factory.maxRetries = maxRetries

    __connect(host, port, factory, connectTimeout, ssl, ssl_CertificateOptions)

    d = factory.handler.waitForConnection()
    d.addCallback(lambda conn: factory.handler)

    return d


def connect_pool(host, port, poolsize=10, isolated=False,
                 connectTimeout=None, waitTimeout=None, maxRetries=5,
                 ssl=False, ssl_CertificateOptions=None):
    factory = MsgpackClientFactory(handler=PooledConnectionHandler,
                                   handlerConfig={'poolsize': poolsize,
                                                  'isolated': isolated},
                                   connectTimeout=connectTimeout,
                                   waitTimeout=waitTimeout)
    factory.maxRetries = maxRetries

    for _ in range(poolsize):
        __connect(host, port, factory, connectTimeout, ssl, ssl_CertificateOptions)

    d = factory.handler.waitForConnection()
    d.addCallback(lambda conn: factory.handler)

    return d

if sys.version_info.major < 3:  # UNIX sockets are not supported for Python 3

    def connect_UNIX(address, connectTimeout=None, waitTimeout=None, maxRetries=5):
        factory = MsgpackClientFactory(connectTimeout=connectTimeout,
                                       waitTimeout=waitTimeout)
        factory.maxRetries = maxRetries

        reactor.connectUNIX(address, factory, timeout=connectTimeout)

        d = factory.handler.waitForConnection()
        d.addCallback(lambda conn: factory.handler)

        return d

    __all__ = ['connect', 'connect_pool', 'connect_UNIX']
else:
    __all__ = ['connect', 'connect_pool']
