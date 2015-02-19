txmsgpackrpc
============

*For the latest source code, see <http://github.com/jakm/txmsgpackrpc>*


``txmsgpackrpc`` is a library for writing asynchronous
[msgpack-rpc](https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md)
servers and clients in Python, using [Twisted framework](http://twistedmatrix.com).
Library is based on [txMsgpack](https://github.com/donalm/txMsgpack), but some
improvements and fixes were made.


Features
--------

- user friendly API
- modular object model
- working timeouts and reconnecting
- connection pool support
- TCP and UNIX sockets

Python 3 note
-------------

Twisted (actually 15.0) doesn't support twisted.internet.unix module
for Python 3, therefore UNIX sockets are not supported.

Dependencies
------------

- msgpack-python <https://pypi.python.org/pypi/msgpack-python/>
- Twisted        <http://twistedmatrix.com/trac/>

Installation
------------

```sh
% python setup.py install
```


Example
-------

...
