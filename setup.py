import distutils.core

distutils.core.setup(
    name = "txmsgpackrpc",
    version = "0.1",
    packages = ["txmsgpackrpc"],
    author = "Jakub Matys",
    author_email = "matys.jakub@gmail.com",
    url = "https://github.com/jakm/txmsgpackrpc",
    license = "MIT",
    description = "txmsgpackrpc is a Twisted library to support msgpack-rpc",
)
