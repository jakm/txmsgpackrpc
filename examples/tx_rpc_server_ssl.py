from twisted.internet import defer, reactor, ssl
from txmsgpackrpc.server import MsgpackRPCServer


class EchoRPC(MsgpackRPCServer):

    def remote_echo(self, value, msgid=None):
        return defer.succeed(value)


def main():
    server = EchoRPC()

    sslContext = ssl.DefaultOpenSSLContextFactory(
                    'examples/cert/example.key',
                    'examples/cert/example.cert')

    reactor.listenSSL(8000, server.getStreamFactory(), sslContext)

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
