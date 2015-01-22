from txmsgpackrpc.factory  import MsgpackServerFactory


class MsgpackRPCServer(object):

    __factory_class = MsgpackServerFactory
    __factory = None

    @property
    def factory(self):
        if not self.__factory:
            self.__factory = self.__factory_class(self)
        return self.__factory


__all__ = ['MsgpackRPCServer']
