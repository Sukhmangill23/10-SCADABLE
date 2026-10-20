"""Bounded, exact-host HTTP requests and cached robots rules for URL discovery."""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from protego import Protego

from ..config import ScraperConfig
from ..limits import HostLimiter
from ..reliability import (
    TRANSIENT_STATUSES,
    CapacityTimeout,
    parse_retry_after,
    retry_delay,
    wait_before_retry,
)
from .urls import DomainScope, normalize_url

logger = logging.getLogger(__name__)


class RequestBlocked(Exception):
    def __init__(self, reason: str, url: str):
        self.reason = reason
        self.url = url
        super().__init__(f"{reason}: {url}")


@dataclass(frozen=True)
class HttpDocument:
    url: str
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


class GuardedHttpClient:
    """A discovery-session client. Every redirect hop is checked before requesting it.

    Requests are sequential and paced within this session, so sitemap/index fanout cannot
    bypass rate limits. Robot retrieval failures are cached as failures for the session.
    """

    def __init__(
        self,
        homepage: str,
        settings: ScraperConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        host_limiter: HostLimiter | None = None,
    ):
        self.settings = settings
        self._host_limiter = host_limiter
        self.scope = DomainScope(homepage, settings)
        self._client = httpx.AsyncClient(
            transport=transport,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=False,
            timeout=settings.discovery_timeout_seconds,
            trust_env=False,
        )
        self._robots: dict[str, Protego | RequestBlocked] = {}
        self._robot_locks: dict[str, asyncio.Lock] = {}
        self._request_lock = asyncio.Lock()
        self._last_request: dict[str, float] = {}
        self.request_count = 0
        self.retry_events: list[str] = []
        self._cooldowns: dict[str, float] = {}
        self._blocked_hosts: set[str] = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._client.aclose()

    async def _request(self, url: str) -> HttpDocument:
        for attempt in range(1, self.settings.max_retries + 2):
            try:
                document = await self._request_once(url)
            except RequestBlocked as error:
                transient = error.reason == "network_error" and isinstance(
                    error.__cause__,
                    (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError),
                )
                if not transient or attempt > self.settings.max_retries:
                    raise
                document = None
            if document is not None and document.status not in TRANSIENT_STATUSES:
                return document
            after = parse_retry_after(document.headers.get("retry-after")) if document else None
            host = urlsplit(url).hostname
            delay = retry_delay(attempt, self.settings, retry_after=after)
            if after is not None and self._host_limiter:
                self._host_limiter.defer(url, after, self.settings)
            if delay is None:
                self._blocked_hosts.add(host)
                return document
            if after is not None:
                self._cooldowns[host] = max(self._cooldowns.get(host, 0), time.monotonic() + after)
            if attempt > self.settings.max_retries:
                return document
            event = f"discovery_retry: {url}: attempt {attempt + 1}: delay {delay:.3f}s"
            self.retry_events.append(event)
            logger.info(event)
            await wait_before_retry(delay)
        raise AssertionError("Retry loop must return or raise")

    async def _request_once(self, url: str) -> HttpDocument:
        if not self.scope.allows(url):
            raise RequestBlocked("domain_not_approved", url)
        async with self._request_lock:
            if self.request_count >= self.settings.max_sitemap_requests:
                raise RequestBlocked("sitemap_request_limit", url)
            host = urlsplit(url).hostname
            if host in self._blocked_hosts:
                raise RequestBlocked("retry_after_exceeds_budget", url)
            delay = random.uniform(*self.settings.request_delay_seconds)
            parts = urlsplit(url)
            origin = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
            rules = self._robots.get(origin)
            if isinstance(rules, Protego):
                delay = max(delay, self._minimum_delay(rules))
            remaining = delay - (time.monotonic() - self._last_request.get(host, 0.0))
            remaining = max(remaining, self._cooldowns.get(host, 0) - time.monotonic())
            if self._host_limiter:
                try:
                    await self._host_limiter.pace(url, self.settings, delay)
                except CapacityTimeout as error:
                    raise RequestBlocked("retry_after_exceeds_budget", url) from error
            elif remaining > 0:
                await asyncio.sleep(remaining)
            self.request_count += 1
            self._last_request[host] = time.monotonic()
            try:
                async with self._client.stream("GET", url) as response:
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        chunks.extend(chunk)
                        if len(chunks) > self.settings.max_sitemap_bytes:
                            raise RequestBlocked("response_too_large", url)
                    location = response.headers.get("location")
                    document = HttpDocument(
                        str(response.url),
                        response.status_code,
                        bytes(chunks),
                        dict(response.headers),
                    )
                    if response.is_redirect and location:
                        return HttpDocument(
                            urljoin(str(response.url), location), response.status_code, b""
                        )
                    return document
            except httpx.HTTPError as error:
                raise RequestBlocked("network_error", url) from error

    async def _follow(self, url: str, *, robots: bool) -> HttpDocument:
        for redirects in range(self.settings.max_redirects + 1):
            normalized = normalize_url(url)
            if normalized is None or not self.scope.allows(url):
                raise RequestBlocked("domain_not_approved", url)
            url = normalized.absolute
            if robots:
                await self.check(url)
            document = await self._request(url)
            if document.status not in (301, 302, 303, 307, 308):
                return document
            if redirects == self.settings.max_redirects:
                raise RequestBlocked("redirect_limit", url)
            if document.url == url:
                raise RequestBlocked("invalid_redirect", url)
            url = document.url
        raise AssertionError("Redirect loop exceeded its configured bound")

    async def robots_for(self, url: str) -> Protego:
        parts = urlsplit(url)
        origin = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
        async with self._robot_locks.setdefault(origin, asyncio.Lock()):
            if origin not in self._robots:
                target = origin + "/robots.txt"
                try:
                    document = await self._follow(target, robots=False)
                    if document.status in (404, 410):
                        rules = Protego.parse("")
                    elif document.status == 200:
                        rules = Protego.parse(document.body.decode("utf-8", errors="replace"))
                    elif document.status in (401, 403):
                        raise RequestBlocked("robots_disallowed", target)
                    else:
                        raise RequestBlocked("robots_unavailable", target)
                    self._robots[origin] = rules
                except RequestBlocked as error:
                    self._robots[origin] = error
            rules = self._robots[origin]
            if isinstance(rules, RequestBlocked):
                raise rules
            return rules

    def _minimum_delay(self, rules: Protego) -> float:
        delay = float(rules.crawl_delay(self.settings.user_agent) or 0)
        rate = rules.request_rate(self.settings.user_agent)
        if rate and rate.requests > 0:
            delay = max(delay, rate.seconds / rate.requests)
        return delay

    async def check(self, url: str) -> float:
        """Preflight a page/sitemap URL without fetching its content."""
        if not self.scope.allows(url):
            raise RequestBlocked("domain_not_approved", url)
        rules = await self.robots_for(url)
        if not rules.can_fetch(url, self.settings.user_agent):
            raise RequestBlocked("robots_disallowed", url)
        return self._minimum_delay(rules)

    async def document(self, url: str) -> HttpDocument:
        return await self._follow(url, robots=True)
