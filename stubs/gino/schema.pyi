# flake8: noqa
# Stubs for gino.schema (Python 3.7)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from sqlalchemy.sql.ddl import SchemaDropper, SchemaGenerator
from typing import Any, Optional, Coroutine

class AsyncVisitor:
    async def traverse_single(self, obj: Any, **kw: Any): ...

class AsyncSchemaGenerator(AsyncVisitor, SchemaGenerator):
    async def visit_metadata(self, metadata: Any) -> None: ...  # type: ignore
    async def visit_table(self, table: Any, create_ok: bool = ..., include_foreign_key_constraints: Optional[Any] = ..., _is_metadata_operation: bool = ...): ...  # type: ignore
    async def visit_foreign_key_constraint(self, constraint: Any): ...  # type: ignore
    async def visit_sequence(self, sequence: Any, create_ok: bool = ...): ...
    async def visit_index(self, index: Any) -> None: ...  # type: ignore

class AsyncSchemaDropper(AsyncVisitor, SchemaDropper):
    async def visit_metadata(self, metadata: Any): ...  # type: ignore
    async def visit_index(self, index: Any) -> None: ...  # type: ignore
    async def visit_table(self, table: Any, drop_ok: bool = ..., _is_metadata_operation: bool = ...): ...  # type: ignore
    async def visit_foreign_key_constraint(self, constraint: Any): ...  # type: ignore
    async def visit_sequence(self, sequence: Any, drop_ok: bool = ...): ...  # type: ignore

class GinoSchemaVisitor:
    def __init__(self, item: Any) -> None: ...
    async def create(self, bind: Optional[Any] = ..., *args: Any, **kwargs: Any): ...
    async def drop(self, bind: Optional[Any] = ..., *args: Any, **kwargs: Any) -> None: ...
    async def create_all(self, bind: Optional[Any] = ..., tables: Optional[Any] = ..., checkfirst: bool = ...) -> None: ...
    async def drop_all(self, bind: Optional[Any] = ..., tables: Optional[Any] = ..., checkfirst: bool = ...) -> None: ...

class AsyncSchemaTypeMixin:
    async def create_async(self, bind: Optional[Any] = ..., checkfirst: bool = ...) -> None: ...
    async def drop_async(self, bind: Optional[Any] = ..., checkfirst: bool = ...) -> None: ...

class _Async:
    def __init__(self, listener: Any) -> None: ...
    async def call(self, *args: Any, **kw: Any) -> None: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, None]: ...

def patch_schema(db: Any) -> None: ...