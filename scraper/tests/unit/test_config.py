from pathlib import Path

import pytest
from pydantic import ValidationError

from scraper.config import ProjectConfig, ScraperConfig, load_config, resolve_config


def test_override_precedence_preserves_unspecified_nested_settings():
    global_settings = ScraperConfig(
        max_pages=35,
        max_depth=2,
        dynamic={"wait_timeout_seconds": 8, "scan_full_page": True},
        selection={"budget_usd": 0.01, "timeout_seconds": 9},
    )
    competitor = ScraperConfig(
        max_pages=12,
        dynamic={"wait_for_css": "main"},
        selection={"budget_usd": 0.02},
    )
    cli = ScraperConfig(max_pages=5)

    result = resolve_config(global_settings, competitor, cli)

    assert result.max_pages == 5
    assert result.max_depth == 2
    assert result.dynamic.wait_timeout_seconds == 8
    assert result.dynamic.scan_full_page is True
    assert result.dynamic.wait_for_css == "main"
    assert result.selection.budget_usd == 0.02
    assert result.selection.timeout_seconds == 9
    assert global_settings.selection.budget_usd == 0.01


def test_explicit_defaults_and_empty_lists_override_global_values():
    result = resolve_config(
        ScraperConfig(max_pages=10, allowed_domains=["careers.example.com"]),
        ScraperConfig(max_pages=50, allowed_domains=[]),
    )
    assert result.max_pages == 50
    assert result.allowed_domains == []


@pytest.mark.parametrize(
    "patch",
    [
        {"max_pages": 0},
        {"max_pages": True},
        {"max_depth": -1},
        {"max_retries": -1},
        {"max_concurrency": 0},
        {"per_domain_concurrency": 0},
        {"page_timeout_seconds": 0},
        {"request_delay_seconds": [2, 1]},
        {"request_delay_seconds": [-1, 2]},
        {"request_delay_seconds": [float("inf"), float("inf")]},
        {"respect_robots_txt": False},
        {"allowed_domains": ["https://example.com/path"]},
        {"allowed_domains": ["*.example.com"]},
        {"dynamic": {"max_scroll_steps": 0}},
        {"dynamic": {"scan_full_page": "false"}},
        {"category_keywords": {"pricing": [""]}},
        {"category_keywords": {"unknown_category": ["word"]}},
        {"max_pagez": 10},
    ],
)
def test_invalid_operational_settings_are_rejected(patch):
    with pytest.raises(ValidationError):
        ScraperConfig.model_validate(patch)


def test_load_toml_resolves_each_competitor_independently(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        "[global]\nmax_pages = 20\n"
        '[[competitors]]\nhomepage_url = "https://example.com"\n'
        "[competitors.overrides]\nmax_pages = 3\n"
        '[[competitors]]\nhomepage_url = "https://other.example"\n',
        encoding="utf-8",
    )

    project = load_config(path)

    assert len(project.competitors) == 2
    assert project.competitors[0].display_name == "example.com"
    assert resolve_config(project.global_settings, project.competitors[0].overrides).max_pages == 3
    assert resolve_config(project.global_settings, project.competitors[1].overrides).max_pages == 20


def test_invalid_file_does_not_silently_fall_back_to_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[global]\nmax_pagez = 2\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(path)
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.toml")


def test_example_configuration_loads():
    project = load_config(Path(__file__).parents[2] / "config.example.toml")
    assert project.competitors[0].homepage_url.host == "example.com"


def test_input_json_round_trip_keeps_overrides_partial():
    project = ProjectConfig.model_validate(
        {
            "global": {"max_pages": 20, "dynamic": {"scan_full_page": True}},
            "competitors": [
                {
                    "homepage_url": "https://example.com/",
                    "overrides": {
                        "max_depth": 1,
                        "dynamic": {"wait_for_css": "main"},
                    },
                }
            ],
        }
    )
    restored = ProjectConfig.model_validate_json(project.model_dump_json())
    resolved = resolve_config(restored.global_settings, restored.competitors[0].overrides)
    assert resolved.max_pages == 20
    assert resolved.max_depth == 1
    assert resolved.dynamic.scan_full_page is True
    assert resolved.dynamic.wait_for_css == "main"
