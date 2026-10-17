from scadable_scraper.config import DynamicSettings, ScraperConfig
from scadable_scraper.crawl4ai_adapter import (
    build_browser_config,
    build_run_config,
    build_seeding_config,
)


def test_browser_and_robots_checks_use_the_same_explicit_identity():
    settings = ScraperConfig(user_agent="SCADABLETestBot/1.0", page_timeout_seconds=12.5)
    browser = build_browser_config(settings)
    run = build_run_config(settings)
    assert browser.headless is True
    assert browser.java_script_enabled is True
    assert browser.accept_downloads is False
    assert browser.ignore_https_errors is False
    assert browser.user_agent == run.user_agent == "SCADABLETestBot/1.0"
    assert run.check_robots_txt is True
    assert run.page_timeout == 12500
    assert run.deep_crawl_strategy is None
    assert run.max_retries == 0  # The service owns the retry budget.


def test_dynamic_options_have_finite_waiting_and_scroll_limits():
    settings = ScraperConfig(
        dynamic={
            "wait_for_css": "main",
            "wait_timeout_seconds": 2.5,
            "scan_full_page": True,
            "max_scroll_steps": 3,
        }
    )
    run = build_run_config(settings)
    assert run.wait_for == "css:main"
    assert run.wait_for_timeout == 2500
    assert run.wait_until == "domcontentloaded"
    assert run.scan_full_page is True
    assert run.max_scroll_steps == 3


def test_rule_settings_can_be_passed_without_replacing_global_configuration():
    settings = ScraperConfig(dynamic={"wait_for_css": "article"})
    run = build_run_config(settings, dynamic=DynamicSettings(wait_for_css="main.jobs"))
    assert run.wait_for == "css:main.jobs"
    assert settings.dynamic.wait_for_css == "article"


def test_run_preserves_source_content_and_links_without_persistent_page_cache():
    run = build_run_config(ScraperConfig())
    assert run.cache_mode.value == "disabled"
    assert run.markdown_generator.content_source == "raw_html"
    assert run.markdown_generator.options["ignore_links"] is False
    assert run.markdown_generator.content_filter is not None
    assert run.word_count_threshold == 0
    assert run.exclude_external_links is False
    assert run.exclude_social_media_links is False
    assert run.remove_overlay_elements is False
    assert run.remove_forms is False
    assert run.extraction_strategy is None
    assert run.verbose is False


def test_application_guard_disables_only_duplicate_sdk_robots_lookup():
    run = build_run_config(ScraperConfig(), application_robots_guard=True)
    assert run.check_robots_txt is False
    assert ScraperConfig().respect_robots_txt is True


def test_sitemap_discovery_does_not_probe_candidate_pages_or_common_crawl(tmp_path):
    settings = ScraperConfig(max_discovered_urls=123, per_domain_concurrency=1)
    config = build_seeding_config(settings, base_directory=tmp_path)
    assert config.source == "sitemap"
    assert config.live_check is False
    assert config.extract_head is False
    assert config.max_urls == 123
    assert config.concurrency == 1
    assert config.filter_nonsense_urls is False  # Our policy records filtering reasons.
    assert config.base_directory == str(tmp_path)
    assert config.force is True
