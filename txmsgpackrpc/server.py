from txmsgpackrpc.factory  import MsgpackServerFactory
from txmsgpackrpc.protocol import MsgpackDatagramProtocol, MsgpackMulticastDatagramProtocol


class MsgpackRPCServer(object):

    def getStreamFactory(self, factory_class=MsgpackServerFactory):
        return factory_class(self)

    def getDatagramProtocol(self, protocol_class=MsgpackDatagramProtocol):
        return protocol_class(handler=self)

    def getMulticastProtocol(self, group, ttl=1, protocol_class=MsgpackMulticastDatagramProtocol):
        return protocol_class(group, ttl, handler=self)


__all__ = ['MsgpackRPCServer']
