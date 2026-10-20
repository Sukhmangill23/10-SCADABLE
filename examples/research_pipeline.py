"""Run from the repository root after installing both packages.

Analyze a saved bundle (no crawling):
    python examples/research_pipeline.py --export scraper/output/run-001/example.com/crawl_summary.json

Collect and analyze fresh content (replace the example URL):
    python examples/research_pipeline.py https://competitor.example/ --max-pages 3

Set OPENAI_API_KEY and OPENAI_MODEL in the root .env or process environment.
Live crawling also requires Chromium; see scraper/docs/quickstart.md for setup.
Results are printed as JSON. Crawl bundles retain the scraper's normal format.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from scraper.environment import load_environment

from llm.analyzer import Analyzer
from llm.client import OpenAIClient
from llm.config import Settings
from llm.pipeline import analyze_export, run_pipeline
from scraper import CompetitorInput, ScraperConfig, SelectionConfig

PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]


async def _run(args):
    client = OpenAIClient(Settings(_env_file=None))
    try:
        analyzer = Analyzer(client)
        if args.summary_path is not None:
            return [await analyze_export(args.summary_path, analyzer=analyzer)]
        output = args.output or (
            PROJECT_DIRECTORY
            / "scraper/output"
            / f"research-{datetime.now(UTC):%Y-%m-%d_%H-%M-%S_%f}_UTC"
        )
        return await run_pipeline(
            [CompetitorInput(homepage_url=url) for url in args.homepages],
            output_directory=output,
            scraper_settings=ScraperConfig(
                max_pages=args.max_pages,
                selection=SelectionConfig(mode=args.selection_mode),
            ),
            analyzer=analyzer,
        )
    finally:
        await client.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "homepages", nargs="*", help="Competitor homepage URLs to collect"
    )
    parser.add_argument(
        "--export", dest="summary_path", type=Path, help="Analyze an existing index"
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Credential file; defaults to the repository-root .env",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Fresh crawl root; defaults to scraper/output/research-<UTC>",
    )
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument(
        "--selection-mode",
        choices=("llm", "structural"),
        default="llm",
        help="Crawl selection only; downstream analysis still uses OpenAI",
    )
    args = parser.parse_args(argv)
    if bool(args.homepages) == (args.summary_path is not None):
        parser.error("Provide homepage URLs or --export, exclusively")
    try:
        load_environment(args.env_file, required=args.env_file is not None)
        results = asyncio.run(_run(args))
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        return 130
    print(json.dumps([result.model_dump(mode="json") for result in results], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
