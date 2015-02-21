# http://github.com/donalm/txMsgpack
# Copyright (c) 2013 Donal McMullan

# https://github.com/jakm/txmsgpackrpc
# Copyright (c) 2015 Jakub Matys

import msgpack
from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet import defer
from twisted.internet import protocol

from txmsgpackrpc.protocol import MsgpackStreamProtocol
from txmsgpackrpc.protocol import MSGTYPE_REQUEST
from txmsgpackrpc.protocol import MSGTYPE_RESPONSE
from txmsgpackrpc.protocol import MSGTYPE_NOTIFICATION


class Echo(MsgpackStreamProtocol):
    def remote_insert_key(self, value, msgid=None):
        value["new_key"]=1
        return self.remote_echo(value, msgid)

    def remote_echo(self, value, msgid=None):
        return value

    def remote_notify(self, value):
        return

    def remote_sum(self, args):
        lhs, rhs = args
        df = defer.Deferred()
        df.callback(lhs + rhs)
        return df


class EchoServerFactory(protocol.Factory):
    protocol = Echo
    sendErrors = True

    def __init__(self, sendErrors=False):
        EchoServerFactory.sendErrors = sendErrors

    def buildProtocol(self, addr):
        return EchoServerFactory.protocol(self, sendErrors=EchoServerFactory.sendErrors)

    def addConnection(self, connection):
        pass

    def delConnection(self, connection):
        pass

    def getRemoteMethod(self, protocol, methodName):
        return getattr(protocol, "remote_" + methodName)


class MsgpackTestCase(unittest.TestCase):
    request_index=0
    def setUp(self):
        factory = EchoServerFactory(True)
        self.proto = factory.buildProtocol(("127.0.0.1", 0))
        self.transport = proto_helpers.StringTransport()
        self.proto.makeConnection(self.transport)
        self.packer = msgpack.Packer(encoding="utf-8")

    def test_request_string(self):
        arg = "SIMON SAYS"
        return self._test_request(value=arg, expected_result=arg, expected_error=None)

    def test_request_dict(self):
        arg = {"A":1234}
        ret = {"A":1234, "new_key":1}
        return self._test_request(method="insert_key", value=arg, expected_result=ret, expected_error=None)

    def test_notify(self):
        arg = "NOTIFICATION"
        return self._test_notification(method="notify", value=arg)

    def test_sum(self):
        args = (2,5)
        ret  = 7
        return self._test_request(method="sum", value=args, expected_result=ret, expected_error=None)

    def _test_notification(self, method="notify", value=""):
        message = (MSGTYPE_NOTIFICATION, method, (value,))
        packed_message = self.packer.pack(message)
        self.proto.dataReceived(packed_message)
        return_value = self.transport.value()
        self.assertEqual(return_value, "")

    def _test_request(self, operation=MSGTYPE_REQUEST, method="echo", value="", expected_result="", expected_error=None):
        index = MsgpackTestCase.request_index
        MsgpackTestCase.request_index += 1

        message         = (operation, index, method, (value,))
        packed_message  = self.packer.pack(message)

        response        = (MSGTYPE_RESPONSE, index, expected_error, expected_result)
        packed_response = self.packer.pack(response)

        self.proto.dataReceived(packed_message)
        return_value = self.transport.value()

        self.assertEqual(return_value, packed_response)

        unpacked_response = msgpack.loads(return_value)
        (msgType, msgid, methodName, params) = unpacked_response

        self.assertEqual(msgType, MSGTYPE_RESPONSE)
        self.assertEqual(msgid, index)
        self.assertEqual(methodName, None)
        self.assertEqual(params, expected_result)
