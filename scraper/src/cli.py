"""Standalone CLI. stdout is reserved for structured output; diagnostics use stderr."""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from contextlib import aclosing, contextmanager
from io import TextIOWrapper
from pathlib import Path

from .config import CompetitorInput, ProjectConfig, ScraperConfig, load_config, resolve_config
from .models import CrawlRunDocument
from .output import JsonlSink, atomic_json_file, write_json
from .service import CompetitorScraper


@contextmanager
def _utf8_stdout():
    """Encode redirected Windows output as UTF-8 without closing/reconfiguring stdout."""
    if not hasattr(sys.stdout, "buffer"):
        yield sys.stdout
        return
    sys.stdout.flush()
    stream = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n", write_through=True)
    try:
        yield stream
    finally:
        try:
            stream.flush()
        finally:
            stream.detach()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover and scrape competitor websites with Crawl4AI"
    )
    parser.add_argument(
        "homepages", nargs="*", help="Homepage URLs; select matching TOML overrides when present"
    )
    parser.add_argument("--config", type=Path, help="TOML global settings and competitors")
    parser.add_argument(
        "--output", "-o", default="output/crawl.json", help="UTF-8 output path or '-' for stdout"
    )
    parser.add_argument("--format", choices=("json", "jsonl"), default="json")
    parser.add_argument(
        "--overwrite", action="store_true", help="Allow replacing an existing output file"
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


async def _run(args, competitors, project, overrides, stream) -> int:
    service = CompetitorScraper()
    results = []
    sink = JsonlSink(stream)
    failed = False
    async with aclosing(
        service.crawl_many(competitors, project.global_settings, cli_overrides=overrides)
    ) as iterator:
        async for result in iterator:
            failed |= result.run_status != "success"
            if args.format == "jsonl":
                for page in result.pages:
                    await sink.write_page(page)
                await sink.write_summary(result)
            else:
                results.append(result)
    if args.format == "json":
        write_json(CrawlRunDocument(results=results), stream)
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
        if args.output == "-":
            context = _utf8_stdout()
        else:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            context = (
                atomic_json_file(target, overwrite=args.overwrite)
                if args.format == "json"
                else target.open("w" if args.overwrite else "x", encoding="utf-8", newline="\n")
            )
        with context as stream:
            return asyncio.run(_run(args, competitors, project, overrides, stream))
    except KeyboardInterrupt:
        print("Crawl interrupted", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
