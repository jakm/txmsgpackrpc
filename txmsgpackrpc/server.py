from txmsgpackrpc.factory  import MsgpackServerFactory


class MsgpackRPCServer(object):

    def listenTCP(self, port, **kwargs):
        from twisted.internet import reactor
        factory = MsgpackServerFactory(self)
        return reactor.listenTCP(port, factory, **kwargs)


__all__ = ['MsgpackRPCServer']
