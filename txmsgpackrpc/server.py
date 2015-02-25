from txmsgpackrpc.factory  import MsgpackServerFactory
from txmsgpackrpc.protocol import MsgpackDatagramProtocol, MsgpackMulticastDatagramProtocol


class MsgpackRPCServer(object):
    """
    msgpack-rpc server. Subclass this, implement your own methods. It will
    expose all methods that start with 'remote_' (without the 'remote_' part).

    It contains methods to generate factory and protocol objects that should
    be passed to reactor's listen* methods. Generated objects are binded with
    server.
    """

    def getStreamFactory(self, factory_class=MsgpackServerFactory):
        """
        Generate factory object for TCP, SSL and UNIX sockets.

        @param factory_class: factory class to be instantiated. Default is C{MsgpackServerFactory}.
        @type factory_class: C{type}.
        @return factory object
        @rtype C{t.i.p.Factory}
        """
        return factory_class(self)

    def getDatagramProtocol(self, protocol_class=MsgpackDatagramProtocol):
        """
        Generate protocol object for UDP sockets.

        @param factory_class: protocol class to be instantiated. Default is C{MsgpackDatagramProtocol}.
        @type factory_class: C{type}.
        @return protocol object
        @rtype C{t.i.p.DatagramProtocol}
        """
        return protocol_class(handler=self)

    def getMulticastProtocol(self, group, ttl=1, protocol_class=MsgpackMulticastDatagramProtocol):
        """
        Generate protocol object for multicast UDP sockets.

        @param group: IP of multicast group that will be joined.
        @type group: C{str}.
        @param ttl: time to live of multicast packets.
        @type ttl: C{int}.
        @param factory_class: protocol class to be instantiated. Default is C{MsgpackMulticastDatagramProtocol}.
        @type factory_class: C{type}.
        @return protocol object
        @rtype C{t.i.p.DatagramProtocol}
        """
        return protocol_class(group, ttl, handler=self)


__all__ = ['MsgpackRPCServer']
