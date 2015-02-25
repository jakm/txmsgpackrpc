txmsgpackrpc
============

For the latest source code, see http://github.com/jakm/txmsgpackrpc

``txmsgpackrpc`` is a library for writing asynchronous
`msgpack-rpc <https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md>`__
servers and clients in Python, using `Twisted
framework <http://twistedmatrix.com>`__. Library is based on
`txMsgpack <https://github.com/donalm/txMsgpack>`__, but some
improvements and fixes were made.

Features
--------

-  user friendly API
-  modular object model
-  working timeouts and reconnecting
-  connection pool support
-  TCP, SSL, UDP and UNIX sockets

Python 3 note
-------------

Twisted (actually 15.0) doesn't support twisted.internet.unix module for
Python 3, therefore UNIX sockets are not supported.

Dependencies
------------

-  msgpack-python https://pypi.python.org/pypi/msgpack-python/
-  Twisted http://twistedmatrix.com/trac/

Installation
------------

.. code:: sh

    % pip install txmsgpackrpc

Debian packages are available on project's `Releases
page <https://github.com/jakm/txmsgpackrpc/releases/latest>`__.

TCP example
-----------

Computation of PI using Chudnovsky algorithm in subprocess. For details,
see http://www.craig-wood.com/nick/articles/pi-chudnovsky/.

Results
~~~~~~~

::

    Computation of PI with 5 places finished in 0.022390 seconds

    Computation of PI with 100 places finished in 0.037856 seconds

    Computation of PI with 1000 places finished in 0.038070 seconds

    Computation of PI with 10000 places finished in 0.073907 seconds

    Computation of PI with 100000 places finished in 6.741683 seconds

    Computation of PI with 5 places finished in 0.001142 seconds

    Computation of PI with 100 places finished in 0.001182 seconds

    Computation of PI with 1000 places finished in 0.001206 seconds

    Computation of PI with 10000 places finished in 0.001230 seconds

    Computation of PI with 100000 places finished in 0.001255 seconds

    Computation of PI with 1000000 places finished in 432.574457 seconds

    Computation of PI with 1000000 places finished in 402.551226 seconds

    DONE

Server
~~~~~~

.. code:: python

    from __future__ import print_function

    from collections import defaultdict
    from twisted.internet import defer, reactor, utils
    from twisted.python import failure
    from txmsgpackrpc.server import MsgpackRPCServer


    pi_chudovsky_bs = '''
    """
    Python3 program to calculate Pi using python long integers, binary
    splitting and the Chudnovsky algorithm

    See: http://www.craig-wood.com/nick/articles/pi-chudnovsky/ for more
    info

    Nick Craig-Wood <nick@craig-wood.com>
    """

    import math
    from time import time

    def sqrt(n, one):
        """
        Return the square root of n as a fixed point number with the one
        passed in.  It uses a second order Newton-Raphson convgence.  This
        doubles the number of significant figures on each iteration.
        """
        # Use floating point arithmetic to make an initial guess
        floating_point_precision = 10**16
        n_float = float((n * floating_point_precision) // one) / floating_point_precision
        x = (int(floating_point_precision * math.sqrt(n_float)) * one) // floating_point_precision
        n_one = n * one
        while 1:
            x_old = x
            x = (x + n_one // x) // 2
            if x == x_old:
                break
        return x

    def pi_chudnovsky_bs(digits):
        """
        Compute int(pi * 10**digits)

        This is done using Chudnovsky's series with binary splitting
        """
        C = 640320
        C3_OVER_24 = C**3 // 24
        def bs(a, b):
            """
            Computes the terms for binary splitting the Chudnovsky infinite series

            a(a) = +/- (13591409 + 545140134*a)
            p(a) = (6*a-5)*(2*a-1)*(6*a-1)
            b(a) = 1
            q(a) = a*a*a*C3_OVER_24

            returns P(a,b), Q(a,b) and T(a,b)
            """
            if b - a == 1:
                # Directly compute P(a,a+1), Q(a,a+1) and T(a,a+1)
                if a == 0:
                    Pab = Qab = 1
                else:
                    Pab = (6*a-5)*(2*a-1)*(6*a-1)
                    Qab = a*a*a*C3_OVER_24
                Tab = Pab * (13591409 + 545140134*a) # a(a) * p(a)
                if a & 1:
                    Tab = -Tab
            else:
                # Recursively compute P(a,b), Q(a,b) and T(a,b)
                # m is the midpoint of a and b
                m = (a + b) // 2
                # Recursively calculate P(a,m), Q(a,m) and T(a,m)
                Pam, Qam, Tam = bs(a, m)
                # Recursively calculate P(m,b), Q(m,b) and T(m,b)
                Pmb, Qmb, Tmb = bs(m, b)
                # Now combine
                Pab = Pam * Pmb
                Qab = Qam * Qmb
                Tab = Qmb * Tam + Pam * Tmb
            return Pab, Qab, Tab
        # how many terms to compute
        DIGITS_PER_TERM = math.log10(C3_OVER_24/6/2/6)
        N = int(digits/DIGITS_PER_TERM + 1)
        # Calclate P(0,N) and Q(0,N)
        P, Q, T = bs(0, N)
        one = 10**digits
        sqrtC = sqrt(10005*one, one)
        return (Q*426880*sqrtC) // T

    if __name__ == "__main__":
        import sys
        digits = int(sys.argv[1])
        pi = pi_chudnovsky_bs(digits)
        print(pi)
    '''


    def set_timeout(deferred, timeout=30):
        def callback(value):
            if not watchdog.called:
                watchdog.cancel()
            return value

        deferred.addBoth(callback)

        watchdog = reactor.callLater(timeout, defer.timeout, deferred)


    class ComputePI(MsgpackRPCServer):

        def __init__(self):
            self.waiting = defaultdict(list)
            self.results = {}

        def remote_PI(self, digits, timeout=None):
            if digits in self.results:
                return defer.succeed(self.results[digits])

            d = defer.Deferred()

            if digits not in self.waiting:
                subprocessDeferred = self.computePI(digits, timeout)

                def callWaiting(res):
                    waiting = self.waiting[digits]
                    del self.waiting[digits]

                    if isinstance(res, failure.Failure):
                        func = lambda d: d.errback(res)
                    else:
                        func = lambda d: d.callback(res)

                    for d in waiting:
                        func(d)

                subprocessDeferred.addBoth(callWaiting)

            self.waiting[digits].append(d)

            return d

        def computePI(self, digits, timeout):
            d = utils.getProcessOutputAndValue('/usr/bin/python', args=('-c', pi_chudovsky_bs, str(digits)))

            def callback((out, err, code)):
                if code == 0:
                    pi = int(out)
                    self.results[digits] = pi
                    return pi
                else:
                    return failure.Failure(RuntimeError('Computation failed: ' + err))

            if timeout is not None:
                set_timeout(d, timeout)

            d.addCallback(callback)

            return d


    def main():
        server = ComputePI()
        reactor.listenTCP(8000, server.getStreamFactory())

    if __name__ == '__main__':
        reactor.callWhenRunning(main)
        reactor.run()

Client
~~~~~~

.. code:: python

    from __future__ import print_function

    import sys
    import time
    from twisted.internet import defer, reactor, task
    from twisted.python import failure

    @defer.inlineCallbacks
    def main():
        try:

            from txmsgpackrpc.client import connect

            c = yield connect('localhost', 8000, waitTimeout=900)

            def callback(res, digits, start_time):
                if isinstance(res, failure.Failure):
                    print('Computation of PI with %d places failed: %s' %
                          (digits, res.getErrorMessage()), end='\n\n')
                else:
                    print('Computation of PI with %d places finished in %f seconds' %
                          (digits, time.time() - start_time), end='\n\n')
                sys.stdout.flush()

            defers = []
            for _ in range(2):
                for digits in (5, 100, 1000, 10000, 100000, 1000000):
                    d = c.createRequest('PI', digits, 600)
                    d.addBoth(callback, digits, time.time())
                    defers.append(d)
                # wait for 30 seconds
                yield task.deferLater(reactor, 30, lambda: None)

            yield defer.DeferredList(defers)

            print('DONE')

        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            reactor.stop()

    if __name__ == '__main__':
        reactor.callWhenRunning(main)
        reactor.run()

Multicast UDP example
---------------------

Example servers join to group 224.0.0.5 and listen on port 8000. Their only
method ``echo`` returns its parameter.

Client joins group to 224.0.0.5, sends multicast request to group on port 8000
and waits for 5 seconds for responses. If some responses are received,
protocol callbacks with tuple of results and individual parts are checked for
errors. If no responses are received, protocol errbacks with TimeoutError.

Because there is no common way to determine number of peers in group,
MsgpackMulticastDatagramProtocol always wait for responses until waitTimeout
expires.

.. code:: sh

    $ # setup multicast routing
    $ ip route add 224.0.0.0/4 dev eth0
    $ echo 1 > /proc/sys/net/ipv4/ip_forward
    $
    $ # start servers listening on port 8000
    $ python examples/tx_rpc_server_udp_multicast.py &
    [1] 3584
    $ python examples/tx_rpc_server_udp_multicast.py &
    [2] 3585
    $ python examples/tx_rpc_server_udp_multicast.py &
    [3] 3586
    $ python examples/tx_rpc_server_udp_multicast.py &
    [4] 3587
    $ python examples/tx_rpc_server_udp_multicast.py &
    [5] 3588
    $
    $ # execute client
    $ python examples/tx_rpc_client_udp_multicast.py
    Received results from 5 peers
    $

Server
~~~~~~

.. code:: python

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


Client
~~~~~~

.. code:: python

    from __future__ import print_function

    from twisted.internet import defer, reactor

    @defer.inlineCallbacks
    def main():
        try:

            from txmsgpackrpc.client import connect_multicast

            c = yield connect_multicast('228.0.0.5', 8000, ttl=5, waitTimeout=5)

            data = {
                        'firstName': 'John',
                        'lastName': 'Smith',
                        'isAlive': True,
                        'age': 25,
                        'height_cm': 167.6,
                        'address': {
                          'streetAddress': "21 2nd Street",
                          "city": 'New York',
                          "state": 'NY',
                          'postalCode': '10021-3100'
                        },
                        'phoneNumbers': [
                          {
                            'type': 'home',
                            'number': '212 555-1234'
                          },
                          {
                            'type': 'office',
                            'number': '646 555-4567'
                          }
                        ],
                        'children': [],
                        'spouse': None
                      }

            results = yield c.createRequest('echo', data)

            assert isinstance(results, tuple)

            print('Received results from %d peers' % len(results))

            for i, result in enumerate(results):
                if result != data:
                    print('Result %d mismatch' % i)
                    print(result)

        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            reactor.stop()

    if __name__ == '__main__':
        reactor.callWhenRunning(main)
        reactor.run()
