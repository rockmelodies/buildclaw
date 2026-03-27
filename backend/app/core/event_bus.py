from __future__ import annotations
"""A lightweight in-process async event bus used to decouple request handling
from deployment execution.
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Event:
    """A generic domain event passed between producers and consumers."""
    type: str
    payload: Any


class AsyncEventBus:
    """Broadcast events to multiple async subscribers using in-memory queues.

    This implementation is intentionally simple for the current single-process
    prototype. It keeps the public interface small so it can later be replaced
    by Redis Streams, Kafka, or another broker without changing caller code.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, asyncio.Queue[Event]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, event: Event) -> None:
        """Fan out an event to all currently registered subscribers."""
        async with self._lock:
            queues = list(self._subscribers.values())

        for queue in queues:
            await queue.put(event)

    async def subscribe(self, maxsize: int = 16) -> tuple[str, asyncio.Queue[Event]]:
        """Create a subscriber queue and return its identifier and queue handle."""
        subscription_id = uuid4().hex
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._subscribers[subscription_id] = queue
        return subscription_id, queue

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscriber so it stops receiving future events."""
        async with self._lock:
            self._subscribers.pop(subscription_id, None)
