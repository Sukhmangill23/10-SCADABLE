"""SDK configuration only. Browser execution is introduced in later stages.

Imports are lazy so backend consumers can use the contracts without loading the SDK.
The frontier, per-domain semaphore, retry policy and redirect checks belong to the service;
the SDK configuration does not enforce those application policies by itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .config import DynamicSettings, ScraperConfig

if TYPE_CHECKING:
    from crawl4ai import BrowserConfig, CrawlerRunConfig, SeedingConfig


def build_browser_config(settings: ScraperConfig) -> BrowserConfig:
    from crawl4ai import BrowserConfig

    return BrowserConfig(
        browser_type="chromium",
        headless=True,
        java_script_enabled=True,
        accept_downloads=False,
        user_agent=settings.user_agent,
        verbose=False,
    )


def build_run_config(
    settings: ScraperConfig, *, dynamic: DynamicSettings | None = None
) -> CrawlerRunConfig:
    from crawl4ai import CacheMode, CrawlerRunConfig
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    interaction = dynamic if dynamic is not None else settings.dynamic
    return CrawlerRunConfig(
        check_robots_txt=settings.respect_robots_txt,
        user_agent=settings.user_agent,
        cache_mode=CacheMode.DISABLED,
        deep_crawl_strategy=None,
        max_retries=0,
        wait_until="domcontentloaded",
        page_timeout=max(1, int(settings.page_timeout_seconds * 1000)),
        wait_for=f"css:{interaction.wait_for_css}" if interaction.wait_for_css else None,
        wait_for_timeout=max(1, int(interaction.wait_timeout_seconds * 1000)),
        scan_full_page=interaction.scan_full_page,
        max_scroll_steps=interaction.max_scroll_steps,
        scroll_delay=interaction.scroll_delay_seconds,
        word_count_threshold=0,
        markdown_generator=DefaultMarkdownGenerator(
            content_source="raw_html",
            options={"ignore_links": False},
        ),
        exclude_external_links=False,
        exclude_social_media_links=False,
        remove_overlay_elements=False,
        remove_forms=False,
        verbose=False,
    )


def build_seeding_config(settings: ScraperConfig, *, base_directory: Path) -> SeedingConfig:
    """Sitemaps only: do not fetch candidate HTML before policy/budget checks."""
    from crawl4ai import SeedingConfig

    return SeedingConfig(
        source="sitemap",
        live_check=False,
        extract_head=False,
        max_urls=settings.max_discovered_urls,
        concurrency=settings.per_domain_concurrency,
        filter_nonsense_urls=False,
        base_directory=str(base_directory),
        force=True,
        verbose=False,
    )
