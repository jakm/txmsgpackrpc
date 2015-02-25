from twisted.internet import defer
from twisted.python import log

from txmsgpackrpc.error import ConnectionError


class SimpleConnectionHandler(object):
    """
    Connection handler that handles connections established by reconnecting
    factory. If connection is not established user requests and notifications
    wait until new connection is made or error is detected.
    """
    def __init__(self, factory):
        self.factory = factory
        self.connection = None
        self._waitingForConnection = set()

    def getConnection(self):
        if self.connection and self.connection.connected:
            return defer.succeed(self.connection)
        else:
            d = self.waitForConnection()
            d.addCallback(lambda handler: handler.getConnection())
            return d

    def createRequest(self, method, *params):
        """
        Create new RPC request. If connection is not established, request will
        be deferred until new connection is made or error is detected.

        Possible exceptions:
        * C{error.ConnectionError}: all connection attempts failed
        * C{error.ResponseError}: remote method returned error value
        * C{error.TimeoutError}: waitTimeout expired during request processing
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        d = self.getConnection()
        d.addCallback(lambda conn: conn.createRequest(method, params))
        return d

    def createNotification(self, method, params):
        """
        Create new RPC notification. If connection is not established, request
        will be deferred until new connection is made or error is detected.

        Possible exceptions:
        * C{error.ConnectionError}: all connection attempts failed
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        d = self.getConnection()
        d.addCallback(lambda conn: conn.createNotification(method, params))
        return d

    def addConnection(self, connection):
        self.connection = connection

        self.callbackWaitingForConnection(lambda d: d.callback(self))

    def delConnection(self, connection):
        self.connection = None

    def waitForConnection(self):
        if not self.factory.continueTrying:
            raise ConnectionError("Not connected")

        if self.connection and self.connection.connected:
            return defer.succeed(self)

        d = defer.Deferred()
        self._waitingForConnection.add(d)
        return d

    def callbackWaitingForConnection(self, func):
        while self._waitingForConnection:
            d = self._waitingForConnection.pop()
            func(d)

    def disconnect(self):
        self.factory.continueTrying = 0
        if self.connection and self.connection.connected:
            self.connection.closeConnection()

        self.callbackWaitingForConnection(lambda d: d.errback(ConnectionError("Not connected")))

        return defer.succeed(None)


class PooledConnectionHandler(object):
    """
    Connection handler that handles connections in pool that are established by
    reconnecting factory. If connection is not established user requests and
    notifications wait until new connection is made or error is detected.
    """
    def __init__(self, factory, poolsize=10, isolated=False):
        self.factory = factory
        self.poolsize = poolsize
        self.isolated = isolated

        self.size = 0
        self.pool = []
        self.connectionQueue = defer.DeferredQueue()

        self._waitingForConnection = set()
        self._waitingForEmptyPool = set()

    @defer.inlineCallbacks
    def getConnection(self):
        if not self.factory.continueTrying and not self.size:
            raise ConnectionError("Not connected")

        while True:
            conn = yield self.connectionQueue.get()
            if not conn.connected:
                log.msg("Discarding dead connection.")
            else:
                if not self.isolated:
                    self.connectionQueue.put(conn)
                defer.returnValue(conn)

    def _send(self, msgType, method, params):
        d = self.getConnection()
        def callback(connection):
            try:
                func = getattr(connection, msgType)
                d = func(method, params)
            except:
                self.connectionQueue.put(connection)
                raise

            def put_back(reply):
                self.connectionQueue.put(connection)
                return reply

            d.addBoth(put_back)
            return d
        d.addCallback(callback)
        return d

    def createRequest(self, method, *params):
        """
        Create new RPC request. If there is no established connection in the
        pool, request will be deferred until new connection is made or error is
        detected.

        Possible exceptions:
        * C{error.ConnectionError}: all connection attempts failed
        * C{error.ResponseError}: remote method returned error value
        * C{error.TimeoutError}: waitTimeout expired during request processing
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        return self._send('createRequest', method, params)

    def createNotification(self, method, params):
        """
        Create new RPC notification. If there is no established connection in
        the pool, request will be deferred until new connection is made or error
        is detected.

        Possible exceptions:
        * C{error.ConnectionError}: all connection attempts failed
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        return self._send('createNotification', method, params)

    def addConnection(self, connection):
        self.connectionQueue.put(connection)
        self.pool.append(connection)
        self.size = len(self.pool)

        self.callbackWaitingForConnection(lambda d: d.callback(self))

    def delConnection(self, connection):
        try:
            self.pool.remove(connection)
        except Exception as e:
            log.err("Cannot remove connection from pool: %s" % str(e))

        self.size = len(self.pool)

        if not self.size and self._waitingForEmptyPool:
            while self._waitingForEmptyPool:
                d = self._waitingForEmptyPool.pop()
                d.callback(None)

    def _cancelWaitForEmptyPool(self, deferred):
        self._waitingForEmptyPool.discard(deferred)
        deferred.errback(defer.CancelledError())

    def waitForEmptyPool(self):
        if not self.size:
            return defer.succeed(None)
        d = defer.Deferred(self._cancelWaitForEmptyPool)
        self._waitingForEmptyPool.add(d)
        return d

    def waitForConnection(self):
        if not self.factory.continueTrying:
            raise ConnectionError("Not connected")

        if self.size:
            return defer.succeed(self)

        d = defer.Deferred()
        self._waitingForConnection.add(d)
        return d

    def callbackWaitingForConnection(self, func):
        while self._waitingForConnection:
            d = self._waitingForConnection.pop()
            func(d)

    def disconnect(self):
        self.factory.continueTrying = 0
        for conn in self.pool:
            try:
                conn.closeConnection()
            except:
                pass

        self.callbackWaitingForConnection(lambda d: d.errback(ConnectionError("Not connected")))

        return self.waitForEmptyPool()


__all__ = ['SimpleConnectionHandler', 'PooledConnectionHandler']
