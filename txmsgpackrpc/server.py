from txmsgpackrpc.factory  import MsgpackServerFactory
from txmsgpackrpc.protocol import MsgpackDatagramProtocol


class MsgpackRPCServer(object):

    def getStreamFactory(self, factory_class=MsgpackServerFactory):
        return factory_class(self)

    def getDatagramProtocol(self, protocol_class=MsgpackDatagramProtocol):
        return protocol_class(handler=self)


__all__ = ['MsgpackRPCServer']
