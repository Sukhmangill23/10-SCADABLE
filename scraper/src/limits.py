"""Shared hostname slots and document-start pacing, independent of the browser SDK."""

import asyncio
import random
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from .config import ScraperConfig
from .reliability import CapacityTimeout


class HostLimiter:
    def __init__(self, concurrency: int):
        self.concurrency = concurrency
        self._slots: dict[str, asyncio.Semaphore] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._cooldowns: dict[str, float] = {}
        self._blocked_hosts: set[str] = set()

    def defer(self, url: str, seconds: float, settings: ScraperConfig) -> None:
        host = urlsplit(url).hostname
        if seconds > settings.max_backoff_seconds:
            self._blocked_hosts.add(host)
        else:
            self._cooldowns[host] = max(self._cooldowns.get(host, 0), time.monotonic() + seconds)

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
            while True:
                if host in self._blocked_hosts:
                    raise CapacityTimeout("host_retry_after_exceeds_budget")
                now = time.monotonic()
                delay = max(
                    interval - (now - self._last_request.get(host, 0.0)),
                    self._cooldowns.get(host, 0) - now,
                )
                if delay <= 0:
                    break
                await asyncio.sleep(delay)
            self._last_request[host] = time.monotonic()
