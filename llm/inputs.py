"""Load the scraper's published Markdown bundles without recrawling or cleaning."""

from pathlib import Path

from llm.schemas import AnalysisInput, AnalysisPage
from scraper import CrawlExportSummary


def load_analysis_input(summary_path: str | Path) -> AnalysisInput:
    """Validate a completion index and follow its successful content references.

    Partial-run warnings and failed-page metadata remain in ``crawl_summary``.
    Missing/invalid files fail explicitly. Whitespace-only pages are not analyzed.
    """
    index = Path(summary_path).resolve(strict=True)
    summary = CrawlExportSummary.model_validate_json(index.read_text(encoding="utf-8"))
    bundle = index.parent
    pages = []
    for page in summary.pages:
        if page.status != "success" or page.markdown_file is None:
            continue
        content = (bundle / page.markdown_file).resolve(strict=True)
        if not content.is_relative_to(bundle):
            raise ValueError(
                f"Markdown reference escapes the export bundle: {page.markdown_file}"
            )
        with content.open(encoding="utf-8", newline="") as stream:
            markdown = stream.read()
        if markdown.strip():
            pages.append(AnalysisPage(source=page, markdown=markdown))
    if not pages:
        details = list(summary.warnings)
        details.extend(page.error for page in summary.pages if page.error)
        explanation = (
            "; ".join(dict.fromkeys(details)) or "No successful nonempty Markdown pages"
        )
        raise ValueError(
            f"No usable Markdown pages for {summary.competitor_name} "
            f"({summary.homepage_url}, status={summary.status}). "
            f"Export: {index}. Crawl details: {explanation}"
        )
    return AnalysisInput(crawl_summary=summary, pages=pages)
