class MsgpackError(Exception):
    pass


class ConnectionError(MsgpackError):
    pass


class ResponseError(MsgpackError):
    pass


class InvalidRequest(MsgpackError):
    pass


class InvalidResponse(MsgpackError):
    pass


class InvalidData(MsgpackError):
    pass


class TimeoutError(MsgpackError):
    pass


class SerializationError(MsgpackError):
    pass
