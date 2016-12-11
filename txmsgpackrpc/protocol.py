# http://github.com/donalm/txMsgpack
# Copyright (c) 2013 Donal McMullan

# https://github.com/jakm/txmsgpackrpc
# Copyright (c) 2015 Jakub Matys

from __future__ import print_function

import logging
import msgpack
import sys
from collections import defaultdict, deque, namedtuple
from twisted.internet import defer, protocol
from twisted.protocols import policies
from twisted.python import failure, log

from txmsgpackrpc.error import (ConnectionError, ResponseError, InvalidRequest,
                                InvalidResponse, InvalidData, TimeoutError,
                                SerializationError)


MSGTYPE_REQUEST=0
MSGTYPE_RESPONSE=1
MSGTYPE_NOTIFICATION=2


Context = namedtuple('Context', ['peer'])


class MsgpackBaseProtocol(object):
    """
    msgpack rpc client/server protocol - base implementation
    """
    def __init__(self, sendErrors=False, packerEncoding="utf-8", unpackerEncoding="utf-8", useList=True):
        """
        @param sendErrors: forward any uncaught Exception details to remote peer.
        @type sendErrors: C{bool}.
        @param packerEncoding: encoding used to encode Python str and unicode. Default is 'utf-8'.
        @type packerEncoding: C{str}
        @param unpackerEncoding: encoding used for decoding msgpack bytes. Default is 'utf-8'.
        @type unpackerEncoding: C{str}.
        @param useList: If true, unpack msgpack array to Python list.  Otherwise, unpack to Python tuple.
        @type useList: C{bool}.
        """
        self._sendErrors = sendErrors
        self._incoming_requests = {}
        self._outgoing_requests = {}
        self._next_msgid = 0
        self._packer = msgpack.Packer(encoding=packerEncoding)
        self._unpacker = msgpack.Unpacker(encoding=unpackerEncoding, unicode_errors='strict', use_list=useList)

    def isConnected(self):
        raise NotImplementedError('Must be implemented in descendant')

    def writeRawData(self, message, context):
        raise NotImplementedError('Must be implemented in descendant')

    def getRemoteMethod(self, protocol, methodName):
        raise NotImplementedError('Must be implemented in descendant')

    def getClientContext(self):
        raise NotImplementedError('Must be implemented in descendant')

    def createRequest(self, method, params):
        """
        Create new RPC request. If protocol is not connected, errback with
        C{ConnectionError} will be called.

        Possible exceptions:
        * C{error.ConnectionError}: all connection attempts failed
        * C{error.ResponseError}: remote method returned error value
        * C{error.TimeoutError}: waitTimeout expired during request processing
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple} or C{list}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        if not self.isConnected():
            raise ConnectionError("Not connected")
        msgid = self.getNextMsgid()
        message = (MSGTYPE_REQUEST, msgid, method, params)
        ctx = self.getClientContext()
        self.writeMessage(message, ctx)

        df = defer.Deferred()
        self._outgoing_requests[msgid] = df
        return df

    def createNotification(self, method, params):
        """
        Create new RPC notification. If protocol is not connected, errback with
        C{ConnectionError} will be called.

        Possible exceptions:
        * C{error.ConnectionError}: all connection attempts failed
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple} or C{list}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        if not self.isConnected():
            raise ConnectionError("Not connected")
        if not type(params) in (list, tuple):
            params = (params,)
        message = (MSGTYPE_NOTIFICATION, method, params)
        ctx = self.getClientContext()
        self.writeMessage(message, ctx)

    def getNextMsgid(self):
        self._next_msgid += 1
        return self._next_msgid

    def rawDataReceived(self, data, context=None):
        try:
            self._unpacker.feed(data)
            for message in self._unpacker:
                self.messageReceived(message, context)
        except Exception:
            log.err()

    def messageReceived(self, message, context):
        if message[0] == MSGTYPE_REQUEST:
            return self.requestReceived(message, context)
        if message[0] == MSGTYPE_RESPONSE:
            return self.responseReceived(message)
        if message[0] == MSGTYPE_NOTIFICATION:
            return self.notificationReceived(message)

        return self.undefinedMessageReceived(message)

    def requestReceived(self, message, context):
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

        self._incoming_requests[msgid] = (result, context)

        result.addCallback(self.respondCallback, msgid)
        result.addErrback(self.respondErrback, msgid)
        result.addBoth(self.endRequest, msgid)
        return result

    def callRemoteMethod(self, msgid, methodName, params):
        try:
            method = self.getRemoteMethod(self, methodName)
        except Exception:
            if self._sendErrors:
                raise
            raise InvalidRequest("Client attempted to call unimplemented method: remote_%s" % methodName)

        send_msgid = False
        try:
            # If the remote_method has a keyword argment called msgid, then pass
            # it the msgid as a keyword argument. 'params' is always a list.
            if sys.version_info.major == 2:
                method_arguments = method.func_code.co_varnames
            elif sys.version_info.major == 3:
                method_arguments = method.__code__.co_varnames
            else:
                raise NotImplementedError('Unsupported Python version %s' % sys.version_info.major)

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
            # Response can be delivered after timeout, code below is for debugging
            # if self._sendErrors:
            #     raise
            # raise InvalidResponse("Failed to find dispatched request with msgid %s to match incoming repsonse" % msgid)
            return

        if error is not None:
            # The remote host returned an error, so we need to create a Failure
            # object to pass into the errback chain. The Failure object in turn
            # requires an Exception
            ex = ResponseError(error)
            df.errback(failure.Failure(exc_value=ex))
        else:
            df.callback(result)

    def respondCallback(self, result, msgid):
        try:
            _, ctx = self._incoming_requests[msgid]
        except KeyError:
            ctx = None

        error = None
        response = (MSGTYPE_RESPONSE, msgid, error, result)
        return self.writeMessage(response, ctx)

    def respondErrback(self, f, msgid):
        result = None
        if self._sendErrors:
            error = f.getBriefTraceback()
        else:
            error = f.getErrorMessage()
        self.respondError(msgid, error, result)

    def respondError(self, msgid, error, result=None):
        try:
            _, ctx = self._incoming_requests[msgid]
        except KeyError:
            ctx = None

        response = (MSGTYPE_RESPONSE, msgid, error, result)
        self.writeMessage(response, ctx)

    def writeMessage(self, message, context):
        try:
            message = self._packer.pack(message)
        except Exception:
            self._packer.reset()
            if self._sendErrors:
                raise
            raise SerializationError("ERROR: Failed to write message: %s" % message)

        self.writeRawData(message, context)

    def notificationReceived(self, message):
        # Notifications don't expect a return value, so they don't supply a msgid
        msgid = None

        try:
            (msgType, methodName, params) = message
        except Exception:
            # Log the error - there's no way to return it for a notification
            log.err()

        try:
            result = defer.maybeDeferred(self.callRemoteMethod, msgid, methodName, params)
            result.addBoth(self.notificationCallback)
        except Exception:
            # Log the error - there's no way to return it for a notification
            log.err()

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


class MsgpackStreamProtocol(protocol.Protocol, policies.TimeoutMixin, MsgpackBaseProtocol):
    """
    msgpack rpc client/server stream protocol

    @ivar factory: The L{MsgpackClientFactory} or L{MsgpackServerFactory}  which created this L{Msgpack}.
    """
    def __init__(self, factory, sendErrors=False, timeout=None, packerEncoding="utf-8", unpackerEncoding="utf-8", useList=True):
        """
        @param factory: factory which created this protocol.
        @type factory: C{protocol.Factory}.
        @param sendErrors: forward any uncaught Exception details to remote peer.
        @type sendErrors: C{bool}.
        @param timeout: idle timeout in seconds before connection will be closed.
        @type timeout: C{int}
        @param packerEncoding: encoding used to encode Python str and unicode. Default is 'utf-8'.
        @type packerEncoding: C{str}
        @param unpackerEncoding: encoding used for decoding msgpack bytes. Default is 'utf-8'.
        @type unpackerEncoding: C{str}.
        @param useList: If true, unpack msgpack array to Python list.  Otherwise, unpack to Python tuple.
        @type useList: C{bool}.
        """
        super(MsgpackStreamProtocol, self).__init__(sendErrors, packerEncoding, unpackerEncoding, useList)
        self.factory = factory
        self.setTimeout(timeout)
        self.connected = 0

    def isConnected(self):
        return self.connected == 1

    def writeRawData(self, message, context):
        # transport.write returns None
        self.transport.write(message)

    def getRemoteMethod(self, protocol, methodName):
        return self.factory.getRemoteMethod(self, methodName)

    def getClientContext(self):
        return None

    def dataReceived(self, data):
        self.resetTimeout()

        self.rawDataReceived(data)

    def connectionMade(self):
        # log.msg("connectionMade", logLevel=logging.DEBUG)
        self.connected = 1
        self.factory.addConnection(self)

    def connectionLost(self, reason=protocol.connectionDone):
        # log.msg("connectionLost", logLevel=logging.DEBUG)
        self.connected = 0
        self.factory.delConnection(self)

        self.callbackOutgoingRequests(lambda d: d.errback(reason))

    def timeoutConnection(self):
        # log.msg("timeoutConnection", logLevel=logging.DEBUG)
        self.callbackOutgoingRequests(lambda d: d.errback(TimeoutError("Request timed out")))

        policies.TimeoutMixin.timeoutConnection(self)

    def closeConnection(self):
        self.transport.loseConnection()


class MsgpackDatagramProtocol(protocol.DatagramProtocol, MsgpackBaseProtocol):
    """
    msgpack rpc client/server datagram protocol
    """
    def __init__(self, address=None, handler=None, sendErrors=False, timeout=None, packerEncoding="utf-8",
                 unpackerEncoding="utf-8", useList=True):
        """
        @param address: tuple(host,port) containing address of client where protocol will connect to.
        @type address: C{tuple}.
        @param handler: object of RPC server that will process requests and notifications.
        @type handler: C{server.MsgpackRPCServer}
        @param sendErrors: forward any uncaught Exception details to remote peer.
        @type sendErrors: C{bool}.
        @param timeout: idle timeout in seconds before connection will be closed.
        @type timeout: C{int}
        @param packerEncoding: encoding used to encode Python str and unicode. Default is 'utf-8'.
        @type packerEncoding: C{str}
        @param unpackerEncoding: encoding used for decoding msgpack bytes. Default is 'utf-8'.
        @type unpackerEncoding: C{str}.
        @param useList: If true, unpack msgpack array to Python list.  Otherwise, unpack to Python tuple.
        @type useList: C{bool}.
        """
        super(MsgpackDatagramProtocol, self).__init__(sendErrors, packerEncoding, unpackerEncoding, useList)

        if address:
            if not isinstance(address, tuple) or len(address) != 2:
                raise ValueError('Address must be tuple(host, port)')
            self.conn_address = address
        else:
            self.conn_address = None

        self.handler = handler
        self.timeout = timeout
        self.connected = 0
        self._pendingTimeouts = {}

    def isConnected(self):
        return self.connected == 1

    def writeRawData(self, message, context):
        # transport.write returns None
        self.transport.write(message, context.peer)

    def getRemoteMethod(self, protocol, methodName):
        return getattr(self.handler, "remote_" + methodName)

    def getClientContext(self):
        return Context(peer=self.conn_address)

    def createRequest(self, method, *params):
        """
        Create new RPC request. If protocol is not connected, errback with
        C{ConnectionError} will be called.

        Possible exceptions:
        * C{error.ConnectionError}: protocol is not connected with peer
        * C{error.ResponseError}: remote method returned error value
        * C{error.TimeoutError}: waitTimeout expired during request processing
        * C{t.i.e.ConnectionClosed}: connection closed during request processing

        @param method: RPC method name
        @type method: C{str}
        @param params: RPC method parameters
        @type params: C{tuple} or C{list}
        @return Returns Deferred that callbacks with result of RPC method or
            errbacks with C{error.MsgpackError}.
        @rtype C{t.i.d.Deferred}
        """
        # this method update interface contract in order to be compatible with
        # methods defined by connection handlers
        return super(MsgpackDatagramProtocol, self).createRequest(method, params)

    def writeMessage(self, message, context):
        if self.timeout:
            msgid = message[1]
            from twisted.internet import reactor
            dc = reactor.callLater(self.timeout, self.timeoutRequest, msgid)
            self._pendingTimeouts[msgid] = dc

        return super(MsgpackDatagramProtocol, self).writeMessage(message, context)

    def responseReceived(self, message):
        msgid = message[1]
        dc = self._pendingTimeouts.get(msgid)
        if dc is not None:
            dc.cancel()

        return super(MsgpackDatagramProtocol, self).responseReceived(message)

    def startProtocol(self):
        if self.conn_address:
            host, port = self.conn_address
            self.transport.connect(host, port)
        self.connected = 1

    def datagramReceived(self, data, address):
        ctx = Context(peer=address)
        self.rawDataReceived(data, ctx)

    # Possibly invoked if there is no server listening on the
    # address to which we are sending.
    def connectionRefused(self):
        # log.msg("Connection refused", logLevel=logging.DEBUG)
        self.callbackOutgoingRequests(lambda d: d.errback(ConnectionError("Connection refused")))

    def timeoutRequest(self, msgid):
        # log.msg("timeoutRequest", logLevel=logging.DEBUG)
        try:
            d = self._outgoing_requests.pop(msgid)
            d.errback(TimeoutError("Request timed out"))
        except KeyError:
            log.err("Expired timeout of nonexisting outgoing request %d" % msgid)

    def closeConnection(self):
        self.connected = 0
        self.transport.stopListening()


class MsgpackMulticastDatagramProtocol(MsgpackDatagramProtocol, MsgpackBaseProtocol):
    """
    msgpack rpc client/server multicast datagram protocol
    """
    def __init__(self, group, ttl, port=None, timeout=30, handler=None, sendErrors=False, packerEncoding="utf-8",
                 unpackerEncoding="utf-8", useList=True):
        """
        @param group: IP of multicast group that will be joined.
        @type group: C{str}.
        @param ttl: time to live of multicast packets.
        @type ttl: C{int}.
        @param port: port where client will send packets.
        @type port: C{int}.
        @param timeout: timeout of client's requests. Protocol always wait for responses until timeout expires. Default is 30 seconds.
        @type timeout: C{int}.
        @param handler: object of RPC server that will process requests and notifications.
        @type handler: C{server.MsgpackRPCServer}
        @param sendErrors: forward any uncaught Exception details to remote peer.
        @type sendErrors: C{bool}.
        @param timeout: idle timeout in seconds before connection will be closed.
        @type timeout: C{int}
        @param packerEncoding: encoding used to encode Python str and unicode. Default is 'utf-8'.
        @type packerEncoding: C{str}
        @param unpackerEncoding: encoding used for decoding msgpack bytes. Default is 'utf-8'.
        @type unpackerEncoding: C{str}.
        @param useList: If true, unpack msgpack array to Python list.  Otherwise, unpack to Python tuple.
        @type useList: C{bool}.
        """
        super(MsgpackMulticastDatagramProtocol, self).__init__(handler=handler, timeout=timeout, sendErrors=sendErrors,
            packerEncoding=packerEncoding, unpackerEncoding=unpackerEncoding, useList=useList)

        self.group = group
        self.ttl = ttl
        self.port = port

        self._multicast_results = defaultdict(deque)

    def getClientContext(self):
        return Context(peer=(self.group, self.port))

    def responseReceived(self, message):
        try:
            (msgType, msgid, error, result) = message
        except Exception as e:
            if self._sendErrors:
                raise
            raise InvalidResponse("Failed to unpack response: %s" % e)

        if msgid not in self._outgoing_requests:
            # Response can be delivered after timeout, code below is for debugging
            # raise InvalidResponse("Failed to find dispatched request with msgid %s to match incoming repsonse" % msgid)
            return

        if error is not None:
            # The remote host returned an error, so we need to create a Failure
            # object to pass into the errback chain. The Failure object in turn
            # requires an Exception
            ex = ResponseError(error)
            self._multicast_results[msgid].append(failure.Failure(exc_value=ex))
        else:
            self._multicast_results[msgid].append(result)

    def timeoutRequest(self, msgid):
        # log.msg("timeoutRequest", logLevel=logging.DEBUG)
        try:
            try:
                d = self._outgoing_requests.pop(msgid)
            except KeyError:
                log.err("Expired timeout of nonexisting outgoing request %d" % msgid)
                return

            results = self._multicast_results.get(msgid)

            if results is not None and len(results) > 0:
                d.callback(tuple(results))
            else:
                d.errback(TimeoutError("Request timed out"))
        finally:
            if msgid in self._multicast_results:
                del self._multicast_results[msgid]

    def startProtocol(self):
        self.transport.setTTL(self.ttl)
        self.transport.joinGroup(self.group)
        self.connected = 1


__all__ = ['MsgpackStreamProtocol', 'MsgpackDatagramProtocol', 'MsgpackMulticastDatagramProtocol']
