from __future__ import annotations

import attr
import asyncio
import discord
import pendulum

from typing import (
    Any,
    Optional,
    Iterable,
    Callable,
    Coroutine,
    TypeVar,
    Type,
    Tuple,
    Dict,
)
from typing_extensions import Protocol
from sortedcontainers import SortedKeyList


T = TypeVar('T', bound='DelayedAction')


class DelayedAction(Protocol):
    @property
    def created_at(self) -> pendulum.DateTime:
        ...

    @property
    def end_time(self) -> pendulum.DateTime:
        ...

    @property
    def run(self: T) -> Callable[[T], Coroutine[Any, Any, None]]:
        ...

    @property
    def id_key(self: T) -> Tuple[Type[T], Tuple[Any, ...]]:
        ...


@attr.s(slots=True, auto_attribs=True)
class DelayQueue(object):
    loop: asyncio.AbstractEventLoop

    queue: 'asyncio.Queue[DelayedAction]' = attr.ib(init=False)
    actions: SortedKeyList[DelayedAction] = attr.ib(init=False)
    id_map: Dict[Tuple[Type[DelayedAction], Tuple[Any, ...]], DelayedAction] = attr.ib(
        init=False
    )

    task: Optional[asyncio.Future] = attr.ib(init=False)
    event_task: asyncio.Future = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        self.queue = asyncio.Queue(loop=self.loop)
        self.actions = SortedKeyList(key=lambda x: (x.end_time, x.id_key))
        self.id_map = {}

        async def handle_queue_event() -> None:
            action = await self.queue.get()
            await action.run(action)

        self.event_task = asyncio.create_task(handle_queue_event())

    async def __wait_next(self) -> None:
        action = self.actions[0]
        delta = action.end_time - pendulum.now()

        if delta.total_seconds() > 0:
            await asyncio.sleep(delta.total_seconds())

        action = self.actions.pop(0)
        del self.id_map[action.id_key]
        self.queue.put_nowait(action)

        self.__schedule_next()

    def __schedule_next(self) -> None:
        if len(self.actions) > 0:
            self.task = self.loop.create_task(self.__wait_next())
        else:
            self.task = None

    def __remove(self, action: DelayedAction) -> None:
        id_key = action.id_key
        if self.task is not None and id_key == self.actions[0].id_key:
            self.task.cancel()
            self.task = None

        try:
            previous_action = self.id_map.get(id_key)
            if previous_action is not None:
                self.actions.remove(previous_action)
                del self.id_map[id_key]
        except ValueError:
            pass

    def add(self, action: DelayedAction) -> None:
        if self.task is not None and action.end_time < self.actions[0].end_time:
            self.task.cancel()
            self.task = None

        self.__remove(action)
        self.actions.add(action)
        self.id_map[action.id_key] = action

        if self.task is None:
            self.__schedule_next()

    def find(
        self, type_: Optional[Type[DelayedAction]] = None, **attrs: Any
    ) -> Optional[DelayedAction]:
        def predicate(elem: Any) -> bool:
            for key, val in attrs.items():
                nested = key.split('__')
                obj = elem
                for sub_key in nested:
                    obj = getattr(obj, sub_key)

                if obj != val:
                    return False
            return True

        def typed_predicate(elem: Any) -> bool:
            return isinstance(elem, type_) and predicate(elem)  # type: ignore

        return discord.utils.find(
            predicate if type_ is None else typed_predicate, self.actions
        )

    def find_and_remove(
        self, type_: Optional[Type[DelayedAction]] = None, **attrs: Any
    ) -> None:
        action = self.find(type_, **attrs)

        if action is not None:
            self.remove(action)

    async def get(self) -> DelayedAction:
        return await self.queue.get()

    def remove(self, action: DelayedAction) -> None:
        self.__remove(action)

        if self.task is None:
            self.__schedule_next()

    def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
        self.event_task.cancel()

    @classmethod
    def create(
        cls, actions: Iterable[DelayedAction], loop: asyncio.AbstractEventLoop
    ) -> DelayQueue:  # noqa: F821
        queue = DelayQueue(loop=loop)
        for action in actions:
            queue.id_map[action.id_key] = action
        queue.actions.update(actions)
        queue.__schedule_next()

        return queue
