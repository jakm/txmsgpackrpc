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
