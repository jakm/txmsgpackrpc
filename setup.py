import distutils.core

__VERSION__ = "0.2"

distutils.core.setup(
    name = "txmsgpackrpc",
    version = __VERSION__,
    packages = ["txmsgpackrpc"],
    author = "Jakub Matys",
    author_email = "matys.jakub@gmail.com",
    url = "https://github.com/jakm/txmsgpackrpc",
    license = "MIT",
    description = "txmsgpackrpc is a Twisted library to support msgpack-rpc",
)
