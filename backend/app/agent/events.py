import asyncio
import logging
from typing import Any, Dict, Set

logger = logging.getLogger("event_bus")


class EventBus:
    """In-process pub/sub so REST actions (e.g. owner approval) reach live voice sessions.

    Single-process only; for multi-instance Cloud Run swap for Redis/PubSub with the same API.
    """

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: Dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Dropping event for slow subscriber: %s", event.get("type"))


event_bus = EventBus()
