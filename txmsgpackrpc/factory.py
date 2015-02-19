from __future__ import print_function

from twisted.internet import protocol

from txmsgpackrpc.protocol import Msgpack
from txmsgpackrpc.handler  import SimpleConnectionHandler


class MsgpackServerFactory(protocol.Factory):
    protocol = Msgpack

    def __init__(self, handler):
        self.handler = handler
        self.connections = set()

    def buildProtocol(self, addr):
        p = self.protocol(self, sendErrors=True)
        return p

    def addConnection(self, connection):
        self.connections.add(connection)

    def delConnection(self, connection):
        self.connections.remove(connection)

    def getRemoteMethod(self, protocol, methodName):
        return getattr(self.handler, "remote_" + methodName)


class MsgpackClientFactory(protocol.ReconnectingClientFactory):
    maxDelay = 12
    protocol = Msgpack

    def __init__(self, handler=SimpleConnectionHandler, connectTimeout=None, waitTimeout=None, handlerConfig={}):
        self.connectTimeout = connectTimeout
        self.waitTimeout = waitTimeout
        self.handler = handler(self, **handlerConfig)

    def buildProtocol(self, addr):
        self.resetDelay()
        p = self.protocol(self, timeout=self.waitTimeout)
        return p

    def clientConnectionFailed(self, connector, reason):
        # print("clientConnectionFailed")
        connector.timeout = self.connectTimeout
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

        if self.maxRetries is not None and (self.retries > self.maxRetries):
            self.handler.callbackWaitingForConnection(lambda d: d.errback(reason))

    def clientConnectionLost(self, connector, reason):
        # print("clientConnectionLost")
        connector.timeout = self.connectTimeout
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

        if self.maxRetries is not None and (self.retries > self.maxRetries):
            self.handler.callbackWaitingForConnection(lambda d: d.errback(reason))

    def addConnection(self, connection):
        self.handler.addConnection(connection)

    def delConnection(self, connection):
        self.handler.delConnection(connection)

    def getRemoteMethod(self, protocol, methodName):
        raise NotImplementedError('Cannot call RPC method on client')


__all__ = ['MsgpackServerFactory', 'MsgpackClientFactory']
