from txmsgpackrpc.factory  import MsgpackServerFactory
from txmsgpackrpc.protocol import MsgpackDatagramProtocol


class MsgpackRPCServer(object):

    __datagram_protocol_class = MsgpackDatagramProtocol
    __datagram_protocol = None
    __factory_class = MsgpackServerFactory
    __factory = None

    @property
    def factory(self):
        if not self.__factory:
            self.__factory = self.__factory_class(self)
        return self.__factory

    @property
    def datagram_protocol(self):
        if not self.__datagram_protocol:
            self.__datagram_protocol = self.__datagram_protocol_class(handler=self)
        return self.__datagram_protocol


__all__ = ['MsgpackRPCServer']
