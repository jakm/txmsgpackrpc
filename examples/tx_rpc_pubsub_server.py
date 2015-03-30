from twisted.internet import defer, reactor, task
from txmsgpackrpc.server import MsgpackRPCPubServer


class EchoRPC(MsgpackRPCPubServer):

    def remote_echo(self, value, msgid=None):
        self.Publish('notification', value)
        return value


def main():
    server = EchoRPC()
    reactor.listenTCP(8000, server.getStreamFactory())

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
