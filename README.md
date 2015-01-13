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


Dependencies
------------

- msgpack-python <https://pypi.python.org/pypi/msgpack-python/>
- Twisted        <http://twistedmatrix.com/trac/>
- zope.interface <https://pypi.python.org/pypi/zope.interface#download>


Installation
------------

```sh
% python setup.py install
```


Example
-------

...
