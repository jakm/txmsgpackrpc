from txmsgpackrpc.factory  import MsgpackServerFactory
from txmsgpackrpc.protocol import MsgpackDatagramProtocol, MsgpackMulticastDatagramProtocol

from txmsgpackrpc.error import (ConnectionError)

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


class MsgpackRPCPubServer(MsgpackRPCServer):
    """
    msgpack-rpc publishing server. This server adds publish/subscribe support to
    the base server class.
    """
    def __init__(self):
        self._topics= {}
        return

    def remote_subscribe(self, peer, topic):
        if not topic in self._topics:
            self._topics[topic] = []
#       @todo : return error if already subscribed
        self._topics[topic].append(peer)
        return 0

    def remote_unsubscribe(self, peer, topic):
        try:
            self._topics[topic].remove(peer)
        except KeyError:
            return

        return 0

    def Publish(self, topic, params):
        unsubscribe_peers = []
        try:
            for peer in self._topics[topic]:
                if self._PublishIfConnected(peer, topic, params) == False:
                    unsubscribe_peers.append(peer)
        except KeyError:
            return

        for peer in unsubscribe_peers:
            self._topics[topic].remove(peer)

    def _PublishIfConnected(self, peer, topic, params):
        try:
            peer.createPublish(topic, params)
        except ConnectionError:
            return False
        return True


__all__ = ['MsgpackRPCServer', 'MsgpackRPCPubServer']
