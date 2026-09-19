"""Typed surface for the generated protobuf envelope."""

class JsonEnvelope:
    json: bytes

    def __init__(self, *, json: bytes = b"") -> None: ...
    def SerializeToString(self) -> bytes: ...

    @classmethod
    def FromString(cls, payload: bytes) -> JsonEnvelope: ...
