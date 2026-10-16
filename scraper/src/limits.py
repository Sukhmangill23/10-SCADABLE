"""Shared hostname slots and document-start pacing, independent of the browser SDK."""

import asyncio
import random
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from .config import ScraperConfig


class HostLimiter:
    def __init__(self, concurrency: int):
        self.concurrency = concurrency
        self._slots: dict[str, asyncio.Semaphore] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}

    @asynccontextmanager
    async def slot(self, url: str):
        host = urlsplit(url).hostname
        gate = self._slots.setdefault(host, asyncio.Semaphore(self.concurrency))
        async with gate:
            yield

    async def pace(self, url: str, settings: ScraperConfig, minimum: float) -> None:
        host = urlsplit(url).hostname
        async with self._locks.setdefault(host, asyncio.Lock()):
            interval = max(minimum, random.uniform(*settings.request_delay_seconds))
            delay = interval - (time.monotonic() - self._last_request.get(host, 0.0))
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request[host] = time.monotonic()
