from __future__ import print_function

from twisted.internet import defer, reactor

@defer.inlineCallbacks
def main():
    try:

        from txmsgpackrpc.client import connect_UDP

        c = yield connect_UDP('127.0.0.1', 8000, waitTimeout=5)

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

        res = yield c.createRequest('echo', data)

        assert data == res
        print(res)

    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        reactor.stop()

if __name__ == '__main__':
    reactor.callWhenRunning(main)
    reactor.run()
