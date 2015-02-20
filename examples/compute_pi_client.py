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
