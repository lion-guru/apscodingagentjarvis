"""
Multi-Stream Data Handling for DevMind IDE.
Manages concurrent data streams for chat, tool results, file changes, terminal output, and WebSocket events.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional


@dataclass
class StreamChannel:
    name: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue())
    subscribers: List[Any] = field(default_factory=list)
    is_active: bool = True

    async def put(self, item: Any) -> None:
        await self.queue.put(item)

    async def get(self) -> Any:
        return await self.queue.get()

    async def subscribe(self, subscriber: Any) -> None:
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)

    async def unsubscribe(self, subscriber: Any) -> None:
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)

    async def broadcast(self, item: Any) -> None:
        for subscriber in self.subscribers:
            if hasattr(subscriber, "send"):
                await subscriber.send(item)


class StreamManager:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.channels: Dict[str, StreamChannel] = {}
        self._active_tasks: List[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def register_stream(self, name: str, stream: AsyncIterator = None) -> str:
        if name not in self.channels:
            self.channels[name] = StreamChannel(name=name)
        if stream is not None:
            task = asyncio.create_task(self._consume_stream(name, stream))
            self._active_tasks.append(task)
        return name

    async def _consume_stream(self, name: str, stream: AsyncIterator) -> None:
        channel = self.channels.get(name)
        if not channel:
            return
        try:
            async for item in stream:
                await channel.put(item)
                await channel.broadcast(item)
        except Exception:
            channel.is_active = False

    async def merge_streams(self, stream_names: List[str], strategy: str = "interleave") -> AsyncIterator:
        channels = [self.channels.get(name) for name in stream_names if name in self.channels]
        if not channels:
            return

        if strategy == "interleave":
            queues = [ch.queue for ch in channels]
            while any(not q.empty() or ch.is_active for q, ch in zip(queues, channels)):
                for q, ch in zip(queues, channels):
                    if not q.empty():
                        try:
                            item = q.get_nowait()
                            yield item
                        except asyncio.QueueEmpty:
                            pass
                await asyncio.sleep(0.001)
        elif strategy == "merge":
            all_items = []
            for ch in channels:
                while not ch.queue.empty():
                    try:
                        all_items.append(ch.queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break
            for item in all_items:
                yield item
        elif strategy == "priority":
            queues = [ch.queue for ch in channels]
            while any(not q.empty() or ch.is_active for q, ch in zip(queues, channels)):
                for q, ch in zip(queues, channels):
                    if not q.empty():
                        try:
                            item = q.get_nowait()
                            yield item
                        except asyncio.QueueEmpty:
                            pass
                await asyncio.sleep(0.001)

    async def multiplex(self, tasks: List, max_concurrent: int = None) -> List[Any]:
        concurrency = max_concurrent or self.max_concurrent
        semaphore = asyncio.Semaphore(concurrency)

        async def _run_task(task):
            async with semaphore:
                if asyncio.iscoroutine(task):
                    return await task
                return task

        coroutines = [_run_task(t) for t in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        return results

    async def broadcast(self, message: Dict[str, Any], channels: List[str]) -> None:
        for name in channels:
            channel = self.channels.get(name)
            if channel:
                await channel.broadcast(message)

    def get_channel(self, name: str) -> Optional[StreamChannel]:
        return self.channels.get(name)

    def list_channels(self) -> List[str]:
        return list(self.channels.keys())

    def get_active_count(self) -> int:
        return sum(1 for ch in self.channels.values() if ch.is_active)

    async def stop_all(self) -> None:
        for ch in self.channels.values():
            ch.is_active = False
        for task in self._active_tasks:
            task.cancel()
        self._active_tasks.clear()


class StreamRouter:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def route(self, event: Dict[str, Any]) -> str:
        event_type = event.get("type", "unknown")
        return event_type

    def register_handler(self, channel: str, handler: Callable) -> None:
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    async def dispatch(self, event: Dict[str, Any]) -> Any:
        channel = self.route(event)
        handlers = self._handlers.get(channel, [])
        results = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(event)
            else:
                result = handler(event)
            results.append(result)
        return results

    def get_handlers(self, channel: str = None) -> Dict[str, List[Callable]]:
        if channel:
            return {channel: self._handlers.get(channel, [])}
        return dict(self._handlers)
