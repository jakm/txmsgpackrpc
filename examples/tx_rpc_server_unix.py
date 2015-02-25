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
    reactor.listenUNIX('/tmp/rpc-server-sock', server.getStreamFactory())

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
