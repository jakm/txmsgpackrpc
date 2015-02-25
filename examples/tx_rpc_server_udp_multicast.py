from twisted.internet import defer, reactor, task
from txmsgpackrpc.server import MsgpackRPCServer


class EchoRPC(MsgpackRPCServer):

    @defer.inlineCallbacks
    def remote_echo(self, value, delay=None, msgid=None):
        if delay is not None:
            yield task.deferLater(reactor, delay, lambda: None)
        defer.returnValue(value)


def main():
    server = EchoRPC()
    reactor.listenMulticast(8000, server.getMulticastProtocol('228.0.0.5', ttl=5),
                            listenMultiple=True)

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
