# http://github.com/donalm/txMsgpack
# Copyright (c) 2013 Donal McMullan

# https://github.com/jakm/txmsgpackrpc
# Copyright (c) 2015 Jakub Matys

from __future__ import print_function

import msgpack
from twisted.internet import defer, protocol
from twisted.protocols import policies
from twisted.python import failure

from txmsgpackrpc.error import (ConnectionError, ResponseError, InvalidRequest,
                                InvalidResponse, InvalidData, TimeoutError)


MSGTYPE_REQUEST=0
MSGTYPE_RESPONSE=1
MSGTYPE_NOTIFICATION=2


class Msgpack(protocol.Protocol, policies.TimeoutMixin):
    """
    msgpack rpc client/server protocol

    @ivar factory: The L{MsgpackClientFactory} or L{MsgpackServerFactory}  which created this L{Msgpack}.
    """
    def __init__(self, factory, sendErrors=False, timeout=None, packerEncoding="utf-8", unpackerEncoding="utf-8"):
        """
        @param factory: factory which created this protocol.
        @type factory: C{protocol.Factory}.
        @param sendErrors: forward any uncaught Exception details to remote peer.
        @type sendErrors: C{bool}.
        @param timeout: idle timeout in seconds before connection will be closed.
        @type timeout: C{int}
        @param packerEncoding: encoding used to encode Python str and unicode. Default is 'utf-8'.
        @type packerEncoding: C{str}
        @param unpackerEncoding: encoding used for decoding msgpack bytes. If None (default), msgpack bytes are deserialized to Python bytes.
        @type unpackerEncoding: C{str}.
        """
        self.factory = factory
        self._sendErrors = sendErrors
        self._incoming_requests = {}
        self._outgoing_requests = {}
        self._next_msgid = 0
        self._packer = msgpack.Packer(encoding=packerEncoding)
        self._unpacker = msgpack.Unpacker(encoding=unpackerEncoding, unicode_errors='strict')
        self.setTimeout(timeout)
        self.connected = 0

    def createRequest(self, method, params):
        if not self.connected:
            raise ConnectionError("Not connected")
        msgid = self.getNextMsgid()
        message = (MSGTYPE_REQUEST, msgid, method, params)
        self.writeMessage(message)

        df = defer.Deferred()
        self._outgoing_requests[msgid] = df
        return df

    def createNotification(self, method, params):
        if not self.connected:
            raise ConnectionError("Not connected")
        if not type(params) in (list, tuple):
            params = (params,)
        message = (MSGTYPE_NOTIFICATION, method, params)
        self.writeMessage(message)

    def getNextMsgid(self):
        self._next_msgid += 1
        return self._next_msgid

    def dataReceived(self, data):
        self.resetTimeout()

        self._unpacker.feed(data)
        for message in self._unpacker:
            self.messageReceived(message)

    def messageReceived(self, message):
        if message[0] == MSGTYPE_REQUEST:
            return self.requestReceived(message)
        if message[0] == MSGTYPE_RESPONSE:
            return self.responseReceived(message)
        if message[0] == MSGTYPE_NOTIFICATION:
            return self.notificationReceived(message)

        return self.undefinedMessageReceived(message)

    def requestReceived(self, message):
        try:
            (msgType, msgid, methodName, params) = message
        except ValueError:
            if self._sendErrors:
                raise
            if not len(message) == 4:
                raise InvalidData("Incorrect message length. Expected 4; received %s" % len(message))
            raise InvalidData("Failed to unpack request.")
        except Exception:
            if self._sendErrors:
                raise
            raise InvalidData("Unexpected error. Failed to unpack request.")

        if msgid in self._incoming_requests:
            raise InvalidRequest("Request with msgid '%s' already exists" % msgid)

        result = defer.maybeDeferred(self.callRemoteMethod, msgid, methodName, params)

        self._incoming_requests[msgid] = result

        result.addCallback(self.respondCallback, msgid)
        result.addErrback(self.respondErrback, msgid)
        result.addBoth(self.endRequest, msgid)
        return result

    def callRemoteMethod(self, msgid, methodName, params):
        try:
            method = self.factory.getRemoteMethod(self, methodName)
        except Exception:
            if self._sendErrors:
                raise
            raise InvalidRequest("Client attempted to call unimplemented method: remote_%s" % methodName)

        send_msgid = False
        try:
            # If the remote_method has a keyword argment called msgid, then pass
            # it the msgid as a keyword argument. 'params' is always a list.
            method_arguments = method.func_code.co_varnames
            if 'msgid' in method_arguments:
                send_msgid = True
        except Exception:
            pass


        try:
            if send_msgid:
                result = method(*params, msgid=msgid)
            else:
                result = method(*params)
        except TypeError:
            if self._sendErrors:
                raise
            raise InvalidRequest("Wrong number of arguments for %s" % methodName)

        return result

    def endRequest(self, result, msgid):
        if msgid in self._incoming_requests:
            del self._incoming_requests[msgid]
        return result

    def responseReceived(self, message):
        try:
            (msgType, msgid, error, result) = message
        except Exception as e:
            if self._sendErrors:
                raise
            raise InvalidResponse("Failed to unpack response: %s" % e)

        try:
            df = self._outgoing_requests.pop(msgid)
        except KeyError:
            # There's nowhere to send this error, except the log
            # if self._sendErrors:
            #     raise
            # raise InvalidResponse("Failed to find dispatched request with msgid %s to match incoming repsonse" % msgid)
            pass

        if error is not None:
            # The remote host returned an error, so we need to create a Failure
            # object to pass into the errback chain. The Failure object in turn
            # requires an Exception
            ex = ResponseError(error)
            df.errback(failure.Failure(exc_value=ex))
        else:
            df.callback(result)

    def respondCallback(self, result, msgid):
        error = None
        response = (MSGTYPE_RESPONSE, msgid, error, result)
        return self.writeMessage(response)

    def respondErrback(self, f, msgid):
        """
        """
        result = None
        if self._sendErrors:
            error = f.getBriefTraceback()
        else:
            error = f.getErrorMessage()
        self.respondError(msgid, error, result)

    def respondError(self, msgid, error, result=None):
        response = (MSGTYPE_RESPONSE, msgid, error, result)
        self.writeMessage(response)

    def writeMessage(self, message):
        try:
            message = self._packer.pack(message)
        except Exception:
            if self._sendErrors:
                raise
            raise ConnectionError("ERROR: Failed to write message: %s" % message)

        # transport.write returns None
        self.transport.write(message)

    def notificationReceived(self, message):
        # Notifications don't expect a return value, so they don't supply a msgid
        msgid = None

        try:
            (msgType, methodName, params) = message
        except Exception as e:
            # Log the error - there's no way to return it for a notification
            print(e)
            return

        try:
            result = defer.maybeDeferred(self.callRemoteMethod, msgid, methodName, params)
            result.addBoth(self.notificationCallback)
        except Exception as e:
            # Log the error - there's no way to return it for a notification
            print(e)
            return

        return None

    def notificationCallback(self, result):
        # Log the result if required
        pass

    def undefinedMessageReceived(self, message):
        raise NotImplementedError("Msgpack received a message of type '%s', " \
                                  "and no method has been specified to " \
                                  "handle this." % message[0])

    def callbackOutgoingRequests(self, func):
        while self._outgoing_requests:
            msgid, d = self._outgoing_requests.popitem()
            func(d)

    def connectionMade(self):
        # print("connectionMade")
        self.connected = 1
        self.factory.addConnection(self)

    def connectionLost(self, reason=protocol.connectionDone):
        # print("connectionLost")
        self.connected = 0
        self.factory.delConnection(self)

        self.callbackOutgoingRequests(lambda d: d.errback(reason))

    def timeoutConnection(self):
        # print("timeoutConnection")
        self.callbackOutgoingRequests(lambda d: d.errback(TimeoutError("Request timed out")))

        policies.TimeoutMixin.timeoutConnection(self)

    def closeConnection(self):
        self.transport.loseConnection()


__all__ = ['Msgpack']
