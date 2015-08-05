import sys

import twisted
from twisted.internet import defer, reactor

from txmsgpackrpc.factory  import MsgpackClientFactory
from txmsgpackrpc.handler  import PooledConnectionHandler
from txmsgpackrpc.protocol import MsgpackDatagramProtocol, MsgpackMulticastDatagramProtocol


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
    """
    Connect RPC server via TCP or SSL. Returns C{t.i.d.Deferred} that will
    callback with C{handler.SimpleConnectionHandler} object or errback with
    C{ConnectionError} if all connection attempts will fail.

    @param host: host name.
    @type host: C{str}
    @param port: port number.
    @type port: C{int}
    @param connectTimeout: number of seconds to wait before assuming
        the connection has failed.
    @type connectTimeout: C{int}
    @param waitTimeout: number of seconds the protocol waits for activity
        on a connection before reconnecting it.
    @type waitTimeout: C{int}
    @param maxRetries: maximum number of consecutive unsuccessful connection
        attempts, after which no further connection attempts will be made. If
        this is not explicitly set, no maximum is applied. Default is 5.
    @type maxRetries: C{int}
    @param ssl: use SSL connection instead of TCP. Default is False.
    @type ssl: C{bool}
    @param ssl_CertificateOptions: the security properties for a client or
        server TLS connection used with OpenSSL. If None is passed, function
        create default options object. Default is None.
    @type ssl_CertificateOptions: C{CertificateOptions}
    @return Deferred that callbacks with C{handler.SimpleConnectionHandler}
        object or errbacks with C{ConnectionError}.
    @rtype C{t.i.d.Deferred}
    """
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
    """
    Connect RPC server via TCP or SSL using connection pool. Returns
    C{t.i.d.Deferred} that will callback with C{handler.PooledConnectionHandler}
    object or errback with C{ConnectionError} if all connection attempts
    will fail.

    @param host: host name.
    @type host: C{str}
    @param port: port number.
    @type port: C{int}
    @param poolsize: number of connections in the pool. Default is 10.
    @type poolsize: C{int}
    @param isolated: when True the connection pool allow only one request per
        connection. Default is False.
    @type isolated: C{bool}
    @param connectTimeout: number of seconds to wait before assuming
        the connection has failed.
    @type connectTimeout: C{int}
    @param waitTimeout: number of seconds the protocol waits for activity
        on a connection before reconnecting it.
    @type waitTimeout: C{int}
    @param maxRetries: maximum number of consecutive unsuccessful connection
        attempts, after which no further connection attempts will be made. If
        this is not explicitly set, no maximum is applied. Default is 5.
    @type maxRetries: C{int}
    @param ssl: use SSL connection instead of TCP. Default is False.
    @type ssl: C{bool}
    @param ssl_CertificateOptions: the security properties for a client or
        server TLS connection used with OpenSSL. If None is passed, function
        create default options object. Default is None.
    @type ssl_CertificateOptions: C{CertificateOptions}
    @return Deferred that callbacks with C{handler.PooledConnectionHandler}
        object or errbacks with C{ConnectionError}.
    @rtype C{t.i.d.Deferred}
    """
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


def connect_UDP(host, port, waitTimeout=None):
    """
    Connect RPC server via UDP. Returns C{t.i.d.Deferred} that will
    callback with C{protocol.MsgpackDatagramProtocol} object.

    @param host: IP address of host.
    @type host: C{str}
    @param port: port number.
    @type port: C{int}
    @param waitTimeout: number of seconds the protocol waits for response.
    @type waitTimeout: C{int}
    @return Deferred that callbacks with C{protocol.MsgpackDatagramProtocol}
        object or errbacks with C{ConnectionError}.
    @rtype C{t.i.d.Deferred}
    """
    protocol = MsgpackDatagramProtocol(address=(host, port), timeout=waitTimeout)

    reactor.listenUDP(0, protocol)

    return defer.succeed(protocol)


def connect_multicast(group, port, ttl=1, waitTimeout=None):
    """
    Connect RPC servers via multicast UDP. Returns C{t.i.d.Deferred} that will
    callback with C{protocol.MsgpackMulticastDatagramProtocol} object.

    @param host: IP address of group to join to.
    @type host: C{str}
    @param port: port number.
    @type port: C{int}
    @param ttl: time to live of multicast packets.
    @type ttl: C{int}
    @param waitTimeout: number of seconds the protocol waits for response.
    @type waitTimeout: C{int}
    @return Deferred that callbacks with
        C{protocol.MsgpackMulticastDatagramProtocol} object or errbacks
        with C{ConnectionError}.
    @rtype C{t.i.d.Deferred}
    """
    protocol = MsgpackMulticastDatagramProtocol(group, ttl, port, timeout=waitTimeout)

    reactor.listenMulticast(0, protocol, listenMultiple=True)

    return defer.succeed(protocol)


if sys.version_info.major < 3 or twisted.__version__ >= '15.3.0':  # Twisted <15.3.0 doesn't support UNIX sockets for Python 3

    def connect_UNIX(address, connectTimeout=None, waitTimeout=None, maxRetries=5):
        """
        Connect RPC server via UNIX socket. Returns C{t.i.d.Deferred} that will
        callback with C{handler.SimpleConnectionHandler} object or errback with
        C{ConnectionError} if all connection attempts will fail.

        @param address: path to a unix socket on the filesystem.
        @type address: C{int}
        @param connectTimeout: number of seconds to wait before assuming
            the connection has failed.
        @type connectTimeout: C{int}
        @param waitTimeout: number of seconds the protocol waits for activity
            on a connection before reconnecting it.
        @type waitTimeout: C{int}
        @param maxRetries: maximum number of consecutive unsuccessful connection
            attempts, after which no further connection attempts will be made. If
            this is not explicitly set, no maximum is applied. Default is 5.
        @type maxRetries: C{int}
        @return Deferred that callbacks with C{handler.SimpleConnectionHandler}
            object or errbacks with C{ConnectionError}.
        @rtype C{t.i.d.Deferred}
        """
        factory = MsgpackClientFactory(connectTimeout=connectTimeout,
                                       waitTimeout=waitTimeout)
        factory.maxRetries = maxRetries

        reactor.connectUNIX(address, factory, timeout=connectTimeout)

        d = factory.handler.waitForConnection()
        d.addCallback(lambda conn: factory.handler)

        return d

    __all__ = ['connect', 'connect_pool', 'connect_UDP', 'connect_multicast', 'connect_UNIX']
else:
    __all__ = ['connect', 'connect_pool', 'connect_UDP', 'connect_multicast']
