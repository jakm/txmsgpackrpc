
import inspect
import sys

from txmsgpackrpc.protocol import Msgpack
from txmsgpackrpc.factory  import MsgpackServerFactory


class MsgpackRPCServer(object):

    def _buildFactory(self):
        factory = MsgpackServerFactory()
        factory.server = self
        factory.protocol = self._buildProtocol()

        return factory

    def _buildProtocol(self):
        methods = {}

        for name, member in inspect.getmembers(self):
            if name.startswith('remote_') and inspect.ismethod(member):
                closure = self._createClosure(member)
                methods[name] = closure

        protocol_name = self.__class__.__name__ + '_protocol'

        protocol = type(protocol_name, (Msgpack, object), methods)
        protocol.server = self

        return protocol

    def _createClosure(self, method):
        def protocol_method(proto, *args, **kwargs):
            return method(*args, **kwargs)

        protocol_method.func_name = method.im_func.func_name
        protocol_method.func_doc = getattr(method.im_func, 'func_doc', None)
        protocol_method.func_dict = getattr(method.im_func, 'func_dict', {})
        protocol_method.func_defaults = getattr(method.im_func, 'func_defaults', ())
        callermodule = sys._getframe(3).f_globals.get('__name__', '?')
        protocol_method.__module__ = getattr(method.im_func, 'module', callermodule)

        return protocol_method

    def serve(self, port, backlog=None, interface=None, reactor=None):
        if reactor is None:
            from twisted.internet import reactor

        kwargs = {}

        if backlog is not None:
            kwargs['backlog'] = backlog

        if interface is not None:
            kwargs['interface'] = interface

        factory = self._buildFactory()

        return reactor.listenTCP(port, factory, **kwargs)


__all__ = ['MsgpackRPCServer']
