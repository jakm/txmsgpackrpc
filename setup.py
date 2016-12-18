import os.path
import setuptools


__VERSION__ = "1.2"


# Hard linking doesn't work inside some virtual FS's.
try:
    setup_path = os.path.abspath(__file__)
    linked_path = setup_path + '.lnk'
    os.link(setup_path, linked_path)
    os.unlink(linked_path)
except AttributeError:
    # Windows support of os.link was added in Python 3.2
    pass
except OSError as e:
    import errno
    if e.errno == errno.EPERM:
        del os.link


with open("README.rst") as readme:
    long_description = readme.read()


setuptools.setup(
    name = "txmsgpackrpc",
    version = __VERSION__,
    packages = ["txmsgpackrpc"],
    author = "Jakub Matys",
    author_email = "matys.jakub@gmail.com",
    url = "https://github.com/jakm/txmsgpackrpc",
    license = "MIT",
    description = "txmsgpackrpc is a Twisted library to support msgpack-rpc",
    long_description=long_description,
    install_requires = [
        "Twisted>=16.0",
        "msgpack-python>=0.4",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords = "twisted msgpack rpc",
)
