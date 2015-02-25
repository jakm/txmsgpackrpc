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
