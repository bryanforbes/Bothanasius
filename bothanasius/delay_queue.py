from __future__ import annotations

import attr
import asyncio
import datetime
import discord

from typing import Any, Optional, Iterable, Callable, Coroutine, TypeVar, Generic
from typing_extensions import Protocol
from sortedcontainers import SortedKeyList


T = TypeVar('T', bound='DelayedAction')


class DelayedAction(Protocol):
    created_at: datetime.datetime
    end_time: datetime.datetime


@attr.s(slots=True, auto_attribs=True)
class DelayQueue(Generic[T]):
    loop: asyncio.AbstractEventLoop
    run_action: Callable[[T], Coroutine[Any, Any, None]]

    queue: 'asyncio.Queue[T]' = attr.ib(init=False)
    actions: SortedKeyList[T] = attr.ib(init=False)

    task: Optional[asyncio.Future] = attr.ib(init=False)
    event_task: asyncio.Future = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        self.queue = asyncio.Queue(loop=self.loop)
        self.actions = SortedKeyList(key=lambda x: x.end_time)

        async def handle_queue_event() -> None:
            action = await self.queue.get()
            self.run_action(action)

        self.event_task = asyncio.create_task(handle_queue_event())

    async def __wait_next(self) -> None:
        action = self.actions[0]
        delta = action.end_time - datetime.datetime.now()

        if delta.total_seconds() > 0:
            await asyncio.sleep(delta.total_seconds())

        action = self.actions.pop(0)
        self.queue.put_nowait(action)

        self.__schedule_next()

    def __schedule_next(self) -> None:
        if len(self.actions) > 0:
            self.task = self.loop.create_task(self.__wait_next())
        else:
            self.task = None

    def __remove(self, action: T) -> None:
        if self.task is not None and action is self.actions[0]:
            self.task.cancel()
            self.task = None

        self.actions.remove(action)

    def add(self, action: T) -> None:
        if self.task is not None and action.end_time < self.actions[0].end_time:
            self.task.cancel()
            self.task = None

        self.__remove(action)
        self.actions.add(action)

        if self.task is None:
            self.__schedule_next()

    def find(self, **attrs: Any) -> Optional[T]:
        return discord.utils.get(self.actions, **attrs)

    def find_and_remove(self, **attrs: Any) -> None:
        action = self.find(**attrs)

        if action is not None:
            self.remove(action)

    async def get(self) -> T:
        return await self.queue.get()

    def remove(self, action: T) -> None:
        self.__remove(action)

        if self.task is None:
            self.__schedule_next()

    def stop(self) -> None:
        self.event_task.cancel()
        if self.task is not None:
            self.task.cancel()

    @classmethod
    def create(cls, delays: Iterable[T], run_action: Callable[[T], Coroutine[Any, Any, None]],
               loop: asyncio.AbstractEventLoop) -> DelayQueue[T]:  # noqa: F821
        queue: DelayQueue[T] = DelayQueue(run_action=run_action, loop=loop)
        queue.actions.update(delays)
        queue.__schedule_next()

        return queue
