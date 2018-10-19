# flake8: noqa
# Stubs for gino.dialects.base (Python 3.7)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from ..engine import _DBAPIConnection, _SAConnection, _SAEngine
from ..loader import Loader
from typing import Any, Optional, Type, Generic, TypeVar, AsyncIterator, Generator

DEFAULT: Any
JSON_COLTYPE: int
JSONB_COLTYPE: int

_T = TypeVar('_T')
_U = TypeVar('_U')

class BaseDBAPI:
    paramstyle: str = ...
    Error: Type[Exception] = ...
    @staticmethod
    def Binary(x: Any): ...

class DBAPICursor:
    def execute(self, statement: Any, parameters: Any) -> None: ...
    def executemany(self, statement: Any, parameters: Any) -> None: ...
    @property
    def description(self) -> None: ...
    async def prepare(self, context: Any, clause: Optional[Any] = ...) -> PreparedStatement: ...
    async def async_execute(self, query: Any, timeout: Any, args: Any, limit: int = ..., many: bool = ...) -> None: ...
    def get_statusmsg(self) -> None: ...

class Pool(Generic[_T, _U]):
    @property
    def raw_pool(self) -> _T: ...
    async def acquire(self, *, timeout: Optional[Any] = ...) -> _U: ...
    async def release(self, conn: Any) -> None: ...
    async def close(self) -> None: ...

class Transaction:
    @property
    def raw_transaction(self) -> None: ...
    async def begin(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

class PreparedStatement:
    context: Any = ...
    clause: Any = ...
    def __init__(self, clause: Optional[Any] = ...) -> None: ...
    def iterate(self, *params: Any, **kwargs: Any) -> _PreparedIterableCursor: ...
    async def all(self, *multiparams: Any, **params: Any): ...
    async def first(self, *multiparams: Any, **params: Any): ...
    async def scalar(self, *multiparams: Any, **params: Any): ...
    async def status(self, *multiparams: Any, **params: Any): ...

class _PreparedIterableCursor:
    def __init__(self, prepared: Any, params: Any, kwargs: Any) -> None: ...
    def __aiter__(self) -> AsyncIterator[Any]: ...
    def __await__(self) -> Generator[Any, None, Cursor]: ...

class _IterableCursor:
    def __init__(self, context: Any) -> None: ...
    def __aiter__(self) -> _LazyIterator: ...
    def __await__(self) -> Generator[Any, None, Any]: ...

class _LazyIterator:
    def __init__(self, init: Any) -> None: ...
    async def __anext__(self) -> Any: ...

class _ResultProxy:
    def __init__(self, context: Any) -> None: ...
    @property
    def context(self): ...
    async def execute(self, one: bool = ..., return_model: bool = ..., status: bool = ...): ...
    def iterate(self) -> _IterableCursor: ...
    async def prepare(self, clause: Any): ...

class Cursor:
    async def many(self, n: Any, *, timeout: Any = ...) -> Any: ...
    async def next(self, *, timeout: Any = ...) -> Any: ...
    async def forward(self, n: Any, *, timeout: Any = ...) -> None: ...

class ExecutionContextOverride:
    def return_model(self) -> bool: ...
    def model(self) -> Any: ...
    def timeout(self) -> int: ...
    def loader(self) -> Any: ...
    def process_rows(self, rows: Any, return_model: bool = ...): ...
    def get_result_proxy(self) -> _ResultProxy: ...

class AsyncDialectMixin:
    cursor_cls: Type[DBAPICursor] = ...
    dbapi_class: Type[BaseDBAPI] = ...
    @classmethod
    def dbapi(cls) -> Type[BaseDBAPI]: ...
    def compile(self, elem: Any, *multiparams: Any, **params: Any) -> Any: ...
    async def init_pool(self, url: Any, loop: Any) -> Pool: ...
    def transaction(self, raw_conn: Any, args: Any, kwargs: Any) -> Transaction: ...
