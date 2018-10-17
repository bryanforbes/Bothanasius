# flake8: noqa
# Stubs for sortedcontainers.sortedset (Python 3.7)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from .sortedlist import SortedList, recursive_repr
from collections import MutableSet, Sequence, Set
from typing import Any, Optional, Union, TypeVar, Iterable, Iterator, Callable, AbstractSet, overload

_T = TypeVar('_T')
_SS = TypeVar('_SS', bound=SortedSet)

class SortedSet(MutableSet[_T], Sequence[_T]):
    def __init__(self, iterable: Optional[Iterable[_T]] = ..., key: Optional[Callable[[_T], Any]] = ...) -> None: ...
    @property
    def key(self) -> Optional[Callable[[_T], Any]]: ...
    def __contains__(self, value: object) -> bool: ...
    @overload
    def __getitem__(self, i: int) -> _T: ...
    @overload
    def __getitem__(self, s: slice) -> Sequence[_T]: ...
    @overload
    def __delitem__(self, i: int) -> None: ...
    @overload
    def __delitem__(self, s: slice) -> None: ...
    def __eq__(self, s: Union[SortedSet[Any], Set[Any]]) -> bool: ...  # type: ignore
    def __ne__(self, s: Union[SortedSet[Any], Set[Any]]) -> bool: ...  # type: ignore
    def __lt__(self, s: Union[SortedSet[Any], Set[Any]]) -> bool: ...
    def __gt__(self, s: Union[SortedSet[Any], Set[Any]]) -> bool: ...
    def __le__(self, s: Union[SortedSet[Any], Set[Any]]) -> bool: ...
    def __ge__(self, s: Union[SortedSet[Any], Set[Any]]) -> bool: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[_T]: ...
    def __reversed__(self) -> Iterator[_T]: ...
    def add(self, value: _T) -> None: ...
    def clear(self) -> None: ...
    def copy(self: _SS) -> _SS: ...
    def __copy__(self: _SS) -> _SS: ...
    def count(self, value: _T) -> int: ...
    def discard(self, value: _T) -> None: ...
    def pop(self, index: int = ...) -> _T: ...
    def remove(self, value: _T) -> None: ...
    def difference(self: _SS, *iterables: Iterable[object]) -> _SS: ...
    def __sub__(self: _SS, iterable: Iterable[object]) -> _SS: ...
    def difference_update(self, *iterables: Iterable[object]) -> _SS: ...
    def __isub__(self, iterable: Iterable[object]) -> _SS: ...  # type: ignore
    def intersection(self, *iterables: Iterable[object]) -> _SS: ...
    def __and__(self, iterable: Iterable[object]) -> _SS: ...  # type: ignore
    def __rand__(self, iterable: Iterable[object]) -> _SS: ...
    def intersection_update(self, *iterables: Iterable[Any]) -> _SS: ...
    def __iand__(self, iterable: Iterable[Any]) -> _SS: ...  # type: ignore
    def symmetric_difference(self, other: Iterable[_T]) -> _SS: ...
    def __xor__(self, other: Iterable[_T]) -> _SS: ...  # type: ignore
    def __rxor__(self, other: Iterable[_T]) -> _SS: ...
    def symmetric_difference_update(self, other: Iterable[_T]) -> _SS: ...
    def __ixor__(self, other: Iterable[_T]) -> _SS: ...  # type: ignore
    def union(self, *iterables: Iterable[_T]) -> _SS: ...
    def __or__(self, iterable: Iterable[_T]) -> _SS: ...  # type: ignore
    def __ror__(self, iterable: Iterable[_T]) -> _SS: ...
    def update(self, *iterables: Iterable[_T]) -> None: ...
    def __ior__(self, iterable: Iterable[_T]) -> None: ...  # type: ignore
