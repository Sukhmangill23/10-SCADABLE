"""Standalone CLI exporting per-competitor Markdown bundles and concise JSON indexes."""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from contextlib import aclosing
from pathlib import Path

from .config import CompetitorInput, ProjectConfig, ScraperConfig, load_config, resolve_config
from .output import competitor_directory, export_competitor
from .service import CompetitorScraper

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover and scrape competitor websites with Crawl4AI"
    )
    parser.add_argument(
        "homepages", nargs="*", help="Homepage URLs; select matching TOML overrides when present"
    )
    parser.add_argument("--config", type=Path, help="TOML global settings and competitors")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output"),
        help="Output directory; each competitor gets Markdown files and crawl_summary.json",
    )
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--strategy", choices=("best_first", "bfs"))
    parser.add_argument("--max-concurrency", type=int)
    parser.add_argument("--verbose", action="store_true")
    return parser


def _inputs(args) -> tuple[list[CompetitorInput], ProjectConfig, ScraperConfig]:
    project = load_config(args.config) if args.config else ProjectConfig()
    configured = {str(item.homepage_url): item for item in project.competitors}
    if len(configured) != len(project.competitors):
        raise ValueError("TOML contains duplicate competitor homepages")
    if args.homepages:
        selected = [CompetitorInput(homepage_url=url) for url in args.homepages]
        competitors = list(
            {
                str(item.homepage_url): configured.get(str(item.homepage_url), item)
                for item in selected
            }.values()
        )
    else:
        competitors = project.competitors
    if not competitors:
        raise ValueError("Provide homepage URLs or competitors in --config")
    overrides = ScraperConfig.model_validate(
        {
            key: getattr(args, key)
            for key in ("max_pages", "max_depth", "strategy", "max_concurrency")
            if getattr(args, key) is not None
        }
    )
    for competitor in competitors:
        resolve_config(project.global_settings, competitor.overrides, overrides)
    return competitors, project, overrides


def _prepare_output(directory: Path, competitors: Sequence[CompetitorInput]) -> None:
    if str(directory) == "-":
        raise ValueError("Output must be a directory; stdout export is not supported")
    names = [competitor_directory(str(item.homepage_url)) for item in competitors]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Competitor output folders conflict; use separate output directories")
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = directory / name
        if target.exists() or target.is_symlink():
            raise FileExistsError(
                f"Competitor output exists: {target}; choose a fresh --output directory"
            )


async def _run(args, competitors, project, overrides) -> int:
    service = CompetitorScraper()
    failed = False
    async with aclosing(
        service.crawl_many(competitors, project.global_settings, cli_overrides=overrides)
    ) as iterator:
        async for result in iterator:
            failed |= result.run_status != "success"
            export_competitor(result, args.output)
            logger.info(
                "Saved %s",
                args.output / competitor_directory(str(result.homepage_url)) / "crawl_summary.json",
            )
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    # argparse owns syntax errors/help and their standard SystemExit behavior.
    args = parser.parse_args(argv)
    try:
        competitors, project, overrides = _inputs(args)
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            stream=sys.stderr,
            format="%(levelname)s %(message)s",
        )
        _prepare_output(args.output, competitors)
        return asyncio.run(_run(args, competitors, project, overrides))
    except KeyboardInterrupt:
        print("Crawl interrupted", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
