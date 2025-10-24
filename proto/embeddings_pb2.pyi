from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EmbedRequest(_message.Message):
    __slots__ = ("text", "task_type", "normalize")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TASK_TYPE_FIELD_NUMBER: _ClassVar[int]
    NORMALIZE_FIELD_NUMBER: _ClassVar[int]
    text: str
    task_type: str
    normalize: bool
    def __init__(self, text: _Optional[str] = ..., task_type: _Optional[str] = ..., normalize: bool = ...) -> None: ...

class EmbedResponse(_message.Message):
    __slots__ = ("model_id", "dim", "embedding")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    DIM_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    dim: int
    embedding: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, model_id: _Optional[str] = ..., dim: _Optional[int] = ..., embedding: _Optional[_Iterable[float]] = ...) -> None: ...

class EmbedBatchRequest(_message.Message):
    __slots__ = ("texts", "task_type", "normalize")
    TEXTS_FIELD_NUMBER: _ClassVar[int]
    TASK_TYPE_FIELD_NUMBER: _ClassVar[int]
    NORMALIZE_FIELD_NUMBER: _ClassVar[int]
    texts: _containers.RepeatedScalarFieldContainer[str]
    task_type: str
    normalize: bool
    def __init__(self, texts: _Optional[_Iterable[str]] = ..., task_type: _Optional[str] = ..., normalize: bool = ...) -> None: ...

class EmbedBatchResponse(_message.Message):
    __slots__ = ("model_id", "dim", "items")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    DIM_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    dim: int
    items: _containers.RepeatedCompositeFieldContainer[EmbeddingItem]
    def __init__(self, model_id: _Optional[str] = ..., dim: _Optional[int] = ..., items: _Optional[_Iterable[_Union[EmbeddingItem, _Mapping]]] = ...) -> None: ...

class EmbeddingItem(_message.Message):
    __slots__ = ("index", "embedding")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    index: int
    embedding: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, index: _Optional[int] = ..., embedding: _Optional[_Iterable[float]] = ...) -> None: ...

class HealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthResponse(_message.Message):
    __slots__ = ("status", "model_id", "device", "dim")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    DIM_FIELD_NUMBER: _ClassVar[int]
    status: str
    model_id: str
    device: str
    dim: int
    def __init__(self, status: _Optional[str] = ..., model_id: _Optional[str] = ..., device: _Optional[str] = ..., dim: _Optional[int] = ...) -> None: ...
