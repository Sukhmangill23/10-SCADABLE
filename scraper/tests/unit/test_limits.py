import asyncio
import time

import pytest

from scadable_scraper import ScraperConfig
from scadable_scraper.limits import HostLimiter
from scadable_scraper.reliability import CapacityTimeout


async def test_retry_after_received_during_pacing_extends_the_wait():
    limiter = HostLimiter(1)
    settings = ScraperConfig(request_delay_seconds=(0.0, 0.0))
    limiter.defer("https://example.com", 0.06, settings)
    task = asyncio.create_task(limiter.pace("https://example.com/pricing", settings, 0.0))
    await asyncio.sleep(0.01)
    started = time.monotonic()
    limiter.defer("https://example.com", 0.12, settings)
    await task
    assert time.monotonic() - started >= 0.11


async def test_long_retry_after_stops_a_waiter_already_pacing():
    limiter = HostLimiter(1)
    settings = ScraperConfig(max_backoff_seconds=0.1, request_delay_seconds=(0.0, 0.0))
    limiter.defer("https://example.com", 0.05, settings)
    task = asyncio.create_task(limiter.pace("https://example.com/pricing", settings, 0.0))
    await asyncio.sleep(0.01)
    limiter.defer("https://example.com", 120, settings)
    with pytest.raises(CapacityTimeout):
        await task
