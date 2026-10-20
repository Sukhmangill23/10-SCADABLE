"""Crawl4AI browser boundary with pre-egress document/redirect policy.

Normal browser redirects can bypass Playwright route callbacks. Never fulfill a redirect
response: abort and navigate through the SDK to the separately checked next hop instead.
Third-party rendering resources are permitted; embedded documents/popups are not crawled.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import re
import sys
import time
from collections.abc import Callable
from contextlib import AsyncExitStack, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from .config import DynamicRule, ScraperConfig
from .crawl4ai_adapter import build_browser_config, build_run_config
from .discovery.http import RequestBlocked
from .discovery.urls import DomainScope, normalize_url
from .interfaces import RobotsGuard
from .limits import HostLimiter
from .models import DiscoveredLink, FetchedPage
from .reliability import (
    TRANSIENT_STATUSES,
    CapacityTimeout,
    FetchAttemptError,
    failed_page,
    parse_retry_after,
)
from .runtime import configure_runtime
from .types import WebUrl, utc_now

if TYPE_CHECKING:
    from crawl4ai import CrawlResult

logger = logging.getLogger(__name__)


async def _complete_before_cancelling(operation):
    """Finish bounded SDK work before cancellation can abandon owned subprocesses."""
    task = asyncio.create_task(operation)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Retrieve any error, while preserving the caller's cancellation.
        with suppress(Exception, asyncio.CancelledError):
            task.result()
        raise


def _browser_failure_kind(error: Exception) -> str:
    from playwright.async_api import TimeoutError as PlaywrightTimeout

    if isinstance(error, CapacityTimeout):
        return "capacity"
    if isinstance(error, (TimeoutError, PlaywrightTimeout)):
        return "timeout"
    # Playwright exposes network codes in Error.message rather than typed subclasses.
    message = str(error)
    transient = (
        "ERR_CONNECTION_RESET",
        "ERR_CONNECTION_CLOSED",
        "ERR_CONNECTION_REFUSED",
        "ERR_CONNECTION_TIMED_OUT",
        "ERR_NETWORK_CHANGED",
        "ECONNRESET",
        "ECONNREFUSED",
        "ETIMEDOUT",
        "socket hang up",
    )
    return "network" if any(code in message for code in transient) else "internal"


def _sdk_failure_kind(message: str) -> str:
    # The SDK wraps typed Playwright errors in CrawlResult.error_message. Match only
    # its known wait/navigation envelopes, never arbitrary mentions of "timeout".
    message = message.split("Code context:", 1)[0]
    if re.search(
        r"Wait condition failed: Timeout after \d+ms waiting for selector", message
    ) or re.search(
        r"(?:Wait condition failed:|Page\.(?:goto|wait_for_selector):).*Timeout \d+ms exceeded",
        message,
        re.DOTALL,
    ):
        return "timeout"
    return _browser_failure_kind(Exception(message))


def select_dynamic_rule(url: str, settings: ScraperConfig) -> DynamicRule:
    base = settings.dynamic.model_dump()
    for rule in settings.dynamic_rules:
        if fnmatchcase(url, rule.url_pattern):
            return DynamicRule.model_validate(base | rule.model_dump(exclude_unset=True))
    return DynamicRule(**base, url_pattern="*", max_clicks=0)


async def apply_load_more(page, rule: DynamicRule) -> int:
    if not rule.load_more_selector:
        return 0
    clicks = 0
    for _ in range(rule.max_clicks):
        button = page.locator(rule.load_more_selector).first
        if (
            not await button.count()
            or not await button.is_visible()
            or not await button.is_enabled()
        ):
            break
        await button.click(timeout=rule.wait_timeout_seconds * 1000)
        clicks += 1
        if rule.scroll_delay_seconds:
            await asyncio.sleep(rule.scroll_delay_seconds)
    return clicks


def _json_safe(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def map_sdk_result(
    result: CrawlResult, source_url: str, *, final_url: str, metadata: dict
) -> FetchedPage:
    """Keep SDK-specific values out of application contracts; resolve relative links."""
    md = result.markdown
    raw = md.raw_markdown if md is not None else ""
    filtered = md.fit_markdown if md is not None else None
    values = _json_safe(result.metadata or {})
    values.update(_json_safe(metadata))
    values["response_headers"] = _json_safe(result.response_headers or {})
    links = []
    for group in ("internal", "external"):
        for link in (result.links or {}).get(group, []):
            normalized = normalize_url(link.get("href", ""), base_url=final_url)
            if normalized:
                links.append(
                    DiscoveredLink(
                        url=normalized.absolute,
                        text=link.get("text") or "",
                        title=link.get("title") or None,
                    )
                )
    status = result.status_code
    success = result.success and (status is None or status < 400) and bool(raw.strip())
    if not success:
        kind = (
            "http"
            if status and status >= 400
            else (
                "empty_content" if result.success else _sdk_failure_kind(result.error_message or "")
            )
        )
        values["crawl_diagnostics"] = {"failure_kind": kind}
    return FetchedPage(
        source_url=source_url,
        final_url=final_url,
        page_title=values.get("title") or None,
        crawl_timestamp=utc_now(),
        crawl_status="success" if success else "failed",
        http_status=status,
        raw_markdown=raw,
        filtered_markdown=filtered,
        raw_html=result.html or "",
        metadata=values,
        links=links,
        error_message=None
        if success
        else (
            result.error_message
            or (f"http_{status}" if status and status >= 400 else "empty_markdown")
        ),
    )


@dataclass
class _Attempt:
    expected_url: str
    rule: DynamicRule
    pages: set = field(default_factory=set)
    redirect: str | None = None
    error: str | None = None
    failure_kind: str = "internal"
    blocked_documents: list[str] = field(default_factory=list)
    clicks: int = 0
    active_timeout: asyncio.Timeout | None = None
    paused_seconds: float = 0.0
    retry_after_applied: bool = False


class Crawl4AIFetcher:
    def __init__(
        self,
        homepage: str,
        settings: ScraperConfig,
        robots_guard: RobotsGuard,
        *,
        crawler_factory: Callable | None = None,
        host_limiter: HostLimiter | None = None,
    ):
        self.settings = settings
        self.scope = DomainScope(homepage, settings)
        self.robots = robots_guard
        self._factory = crawler_factory
        self._crawler = None
        self._temporary = None
        self._contexts = set()
        self._context_lock = asyncio.Lock()
        self._states: dict[Any, _Attempt] = {}
        self._current: ContextVar[_Attempt] = ContextVar("crawl_attempt")
        self._local_hosts = HostLimiter(settings.per_domain_concurrency)
        self._shared_hosts = host_limiter

    async def __aenter__(self):
        configure_runtime()
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.async_logger import AsyncLogger
        from rich.console import Console

        self._temporary = TemporaryDirectory(prefix="scraper-crawl-")
        try:
            self._crawler = (self._factory or AsyncWebCrawler)(
                config=build_browser_config(self.settings),
                base_directory=self._temporary.name,
                logger=AsyncLogger(verbose=False, console=Console(stderr=True)),
            )
            self._crawler.crawler_strategy.set_hook("on_page_context_created", self._on_page)
            self._crawler.crawler_strategy.set_hook("before_retrieve_html", self._interact)

            async def start():
                async with asyncio.timeout(self.settings.page_timeout_seconds):
                    await self._crawler.start()

            await _complete_before_cancelling(start())
        except BaseException as error:
            await self.__aexit__(None, None, None)
            if isinstance(error, Exception) and "Executable doesn't exist" in str(error):
                raise RuntimeError(
                    "Chromium is not installed in the selected Playwright cache. "
                    f"Run {sys.executable} -m playwright install chromium "
                    "with the same browser-cache setting used by this process. "
                    f"PLAYWRIGHT_BROWSERS_PATH={os.getenv('PLAYWRIGHT_BROWSERS_PATH', '<default>')}"
                ) from error
            raise
        return self

    async def __aexit__(self, *_):
        try:
            if self._crawler:
                try:

                    async def close():
                        async with asyncio.timeout(10):
                            await self._crawler.close()

                    await _complete_before_cancelling(close())
                except Exception as error:
                    logger.warning("Browser cleanup failed: %s", error)
        finally:
            self._crawler = None
            self._states.clear()
            self._contexts.clear()
            if self._temporary:
                try:
                    self._temporary.cleanup()
                except OSError as error:
                    logger.warning("Browser temporary-file cleanup failed: %s", error)
                self._temporary = None

    async def _check(self, url: str) -> float:
        if normalize_url(url) is None or not self.scope.allows(url):
            raise RequestBlocked("domain_not_approved", url)
        try:
            async with asyncio.timeout(self.settings.discovery_timeout_seconds):
                return await self.robots.check(url)
        except TimeoutError as error:
            raise RequestBlocked("robots_unavailable", url) from error

    async def _on_page(self, page, context, **_):
        state = self._current.get()
        state.pages.add(page)
        self._states[page] = state
        # Bypass service workers so document traffic cannot evade routing.
        session = await context.new_cdp_session(page)
        try:
            await session.send("Network.setBypassServiceWorker", {"bypass": True})
        finally:
            await session.detach()
        async with self._context_lock:
            if context not in self._contexts:
                await context.route("**/*", self._route)
                self._contexts.add(context)
        return page

    async def _interact(self, page, **_):
        state = self._states[page]
        try:
            state.clicks += await apply_load_more(page, state.rule)
        except Exception as error:
            state.error = str(error)
            state.failure_kind = _browser_failure_kind(error)
            raise
        return page

    async def _pace(self, state: _Attempt, url: str, minimum: float) -> None:
        deadline = state.active_timeout
        if deadline is None:
            raise CapacityTimeout("attempt_already_closed")
        loop = asyncio.get_running_loop()
        remaining = max(0.0, deadline.when() - loop.time())
        deadline.reschedule(None)
        started = time.monotonic()
        try:
            async with asyncio.timeout(self.settings.capacity_wait_timeout_seconds):
                await (self._shared_hosts or self._local_hosts).pace(url, self.settings, minimum)
        except CapacityTimeout:
            raise
        except TimeoutError as error:
            raise CapacityTimeout("rate_wait_timeout") from error
        finally:
            state.paused_seconds += time.monotonic() - started
            if state.active_timeout is deadline:
                deadline.reschedule(loop.time() + remaining)
        if state.active_timeout is not deadline:
            raise CapacityTimeout("attempt_already_closed")

    async def _route(self, route):
        from playwright.async_api import Error as PlaywrightError

        request = route.request
        if request.resource_type != "document":
            with suppress(PlaywrightError):
                await route.continue_()
            return
        try:
            page = request.frame.page
        except PlaywrightError:
            # Popup navigation can precede creation of its frame. Deny it before egress.
            await route.abort()
            return
        state = self._states.get(page)
        if state is None or request.frame != page.main_frame:
            if state and len(state.blocked_documents) < 20:
                state.blocked_documents.append(request.url)
            await route.abort()
            return
        try:
            minimum = await self._check(request.url)
            observed = normalize_url(request.url)
            expected = normalize_url(state.expected_url)
            if request.method != "GET" or observed.absolute != expected.absolute:
                raise RequestBlocked("unexpected_document_navigation", request.url)
            await self._pace(state, request.url, minimum)
            response = await route.fetch(
                max_redirects=0, max_retries=0, timeout=self.settings.page_timeout_seconds * 1000
            )
            try:
                if response.status in TRANSIENT_STATUSES:
                    after = parse_retry_after(response.headers.get("retry-after"))
                    if after is not None:
                        (self._shared_hosts or self._local_hosts).defer(
                            request.url, after, self.settings
                        )
                        state.retry_after_applied = True
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location:
                        raise RequestBlocked("invalid_redirect", request.url)
                    target = urljoin(request.url, location)
                    await self._check(target)
                    state.redirect = target
                    await route.abort()
                else:
                    await route.fulfill(response=response)
            finally:
                await response.dispose()
        except RequestBlocked as error:
            state.error = str(error)
            state.failure_kind = "policy"
            with suppress(PlaywrightError):
                await route.abort()
        except Exception as error:
            # Browser-boundary errors become page outcomes, never unhandled event tasks.
            state.error = f"{type(error).__name__}: {error}"
            state.failure_kind = _browser_failure_kind(error)
            with suppress(Exception):
                await route.abort()

    async def fetch(self, url: WebUrl, settings: ScraperConfig) -> FetchedPage:
        if self._crawler is None:
            raise RuntimeError("Use Crawl4AIFetcher as an async context manager")
        source = str(url)
        current = source
        states = []
        redirects = []
        remaining = settings.page_timeout_seconds
        try:
            for hop in range(settings.max_redirects + 1):
                await self._check(current)
                state = _Attempt(current, select_dynamic_rule(current, settings))
                states.append(state)
                token = self._current.set(state)
                try:
                    config = build_run_config(
                        settings, dynamic=state.rule, application_robots_guard=True
                    )
                    # Our cumulative deadline owns active work. The SDK navigation
                    # timer must also allow the separately bounded routing rate wait.
                    config.page_timeout = max(
                        1, int((remaining + settings.capacity_wait_timeout_seconds) * 1000)
                    )
                    async with AsyncExitStack() as stack:
                        try:
                            async with asyncio.timeout(settings.capacity_wait_timeout_seconds):
                                await stack.enter_async_context(self._local_hosts.slot(current))
                                if self._shared_hosts:
                                    await stack.enter_async_context(
                                        self._shared_hosts.slot(current)
                                    )
                        except TimeoutError as error:
                            raise CapacityTimeout("hostname_capacity_wait_timeout") from error
                        started = time.monotonic()
                        async with asyncio.timeout(remaining) as deadline:
                            state.active_timeout = deadline
                            try:
                                result = await self._crawler.arun(current, config=config)
                            finally:
                                state.active_timeout = None
                        remaining -= max(0, time.monotonic() - started - state.paused_seconds)
                finally:
                    self._current.reset(token)
                if state.error:
                    raise FetchAttemptError(state.error, state.failure_kind)
                if state.redirect:
                    redirects.append(state.redirect)
                    if hop == settings.max_redirects:
                        raise FetchAttemptError("redirect_limit", "policy")
                    current = state.redirect
                    continue
                final = result.redirected_url or current
                await self._check(final)
                return map_sdk_result(
                    result,
                    source,
                    final_url=final,
                    metadata={
                        "redirect_chain": redirects,
                        "load_more_clicks": state.clicks,
                        "blocked_documents": state.blocked_documents,
                        "retry_after_applied": state.retry_after_applied,
                    },
                )
        except Exception as error:
            page = failed_page(
                source,
                error,
                kind="policy"
                if isinstance(error, RequestBlocked)
                else (
                    error.kind
                    if isinstance(error, FetchAttemptError)
                    else _browser_failure_kind(error)
                ),
            )
            return page.model_copy(
                update={"metadata": page.metadata | {"redirect_chain": redirects}}
            )
        finally:
            # The SDK may retain its last headless page; close our pages explicitly.
            for state in states:
                for page in state.pages:
                    self._states.pop(page, None)
                    with suppress(Exception):
                        async with asyncio.timeout(5):
                            await page.close()
