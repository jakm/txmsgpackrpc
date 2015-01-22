from twisted.internet import defer, reactor
from txmsgpackrpc.server import MsgpackRPCServer


class EchoRPC(MsgpackRPCServer):

    def remote_echo(self, value, msgid=None):
        return defer.succeed(value)


def main():
    server = EchoRPC()
    reactor.listenTCP(8000, server.factory)

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
