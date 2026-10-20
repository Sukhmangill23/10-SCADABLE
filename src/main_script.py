import argparse
import asyncio

from config import Settings
from crawling.exporteddatacrawler import ExportedDataCrawler
from llm.analyzer import Analyzer
from llm.client import OpenAIClient
from models.crawl_result import CompetitorURL
from pipeline import run_comparison


async def main(run_dir: str) -> None:
    client = OpenAIClient(Settings(openai_model="gpt-6-luna"))
    try:
        swot = await run_comparison(
            CompetitorURL(name="SCADABLE", url="https://scadable.com"),
            competitors=[
                CompetitorURL(name="Cluely", url="https://cluely.com"),
                CompetitorURL(name="Blue J", url="https://www.bluej.com"),
            ],
            crawler=ExportedDataCrawler(run_dir),
            analyzer=Analyzer(client),
        )
        print(swot.model_dump_json(indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="scraper output folder, e.g. output/manual-...")
    asyncio.run(main(parser.parse_args().run_dir))