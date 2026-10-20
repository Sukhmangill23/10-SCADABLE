import json
from pathlib import Path

from crawling.base import BaseCrawler
from models.crawl_result import CompetitorURL, CrawlResult, ScrapedContent

class ExportedDataCrawler(BaseCrawler):
    def __init__(self, search_dir: str | Path) -> None:
        self.search_dir = Path(search_dir)

    async def crawl(self, competitor: CompetitorURL) -> CrawlResult:
        search_folder = self.search_dir / competitor.url.host
        summary_info_path = search_folder / "crawl_summary.json"
        if not summary_info_path.is_file():
            raise FileNotFoundError(f"No completed export for {competitor.url.host} in {self.search_dir}")
        summary = json.loads(summary_info_path.read_text(encoding="utf-8"))

        pages = []
        for entry in summary["pages"]:
            if entry["status"] != "success":
                continue
            text = (search_folder / entry["markdown_file"]).read_text(encoding="utf-8")
            pages.append(ScrapedContent(url=entry["url"], title=entry.get("title"), text=text))

        return CrawlResult(competitor=competitor, provider="crawl4ai", pages=pages)
    