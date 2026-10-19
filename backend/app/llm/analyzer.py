"""Comparison engine: extract facts, analyze SCADABLE, compare, validate.

Pipeline per competitor run:
    1. extract   - competitor facts with evidence URLs and missing topics
    2. scadable  - SCADABLE baseline analysis (memoized per baseline/prompt/model;
                   runs concurrently with ``extract``)
    3. compare   - competitor profile, competitive signals, four-quadrant SWOT
    4. validate  - drop uncrawled citations, tag evidence status
"""

import asyncio
import json
import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from app.llm.client import LLMClientProtocol
from app.llm.config import LLMSettings
from app.llm.prompts import (
    COMPARISON_PROMPT,
    EXTRACTION_PROMPT,
    PROMPT_VERSION,
    SCADABLE_PROMPT,
)
from app.llm.schemas import (
    AnalysisInput,
    CompanyAnalysis,
    ComparisonResult,
    ExtractedInformation,
    PageInput,
)
from app.llm.usage import UsageTracker, compute_cost_usd, estimate_tokens
from app.llm.validation import (
    build_url_index,
    filter_citations,
    to_swot_entries,
    validate_findings,
)
from app.llm.versioning import build_versions

logger = logging.getLogger(__name__)

STAGES = ("extract", "scadable", "compare", "validate")
# Assumed output size per stage for the pre-call cost estimate.
_ESTIMATED_OUTPUT_TOKENS = {"extract": 2500, "scadable": 600, "compare": 3000}

ProgressCallback = Callable[[dict[str, Any]], None]

# SCADABLE's baseline is static, so its analysis is shared across runs.
_SCADABLE_CACHE: dict[tuple[str, str, str], CompanyAnalysis] = {}


class CostLimitExceeded(RuntimeError):
    """Raised before any API call when the estimated cost exceeds the cap."""


class EmptyInputError(ValueError):
    """Raised when the crawl produced no page text to analyze."""


def clear_scadable_cache() -> None:
    """Drop memoized SCADABLE analyses (used by tests)."""
    _SCADABLE_CACHE.clear()


def prepare_pages(
    scraped_data: Mapping[str, Any],
    max_chars_per_page: int,
    max_total_chars: int,
) -> list[PageInput]:
    """Normalize crawler pages, tolerating missing or extra keys, and trim text."""
    pages: list[PageInput] = []
    remaining = max_total_chars
    for raw in scraped_data.get("pages") or []:
        if not isinstance(raw, Mapping):
            continue
        url = str(raw.get("url") or "").strip()
        body = raw.get("text") or raw.get("markdown") or raw.get("content") or ""
        body = str(body).strip()
        if not url or not body or remaining <= 0:
            continue
        body = body[: min(max_chars_per_page, remaining)]
        remaining -= len(body)
        title = raw.get("title")
        pages.append(PageInput(url=url, title=str(title) if title else None, text=body))
    return pages


def _render_pages(data: AnalysisInput) -> str:
    blocks = [f"<company>{data.company_name}</company>"]
    for page in data.pages:
        title = f"Title: {page.title}\n" if page.title else ""
        blocks.append(f'<page url="{page.url}">\n{title}{page.text}\n</page>')
    return "\n\n".join(blocks)


class Analyzer:
    """Run the multi-stage LLM analysis for one competitor."""

    def __init__(
        self,
        client: LLMClientProtocol,
        settings: LLMSettings | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.client = client
        self.settings = settings or LLMSettings()
        self.progress_callback = progress_callback
        self.usage = UsageTracker(
            model=client.model,
            price_input_per_1m=self.settings.llm_price_input_per_1m,
            price_output_per_1m=self.settings.llm_price_output_per_1m,
        )

    # ------------------------------------------------------------------
    # Progress reporting
    # ------------------------------------------------------------------

    def _emit(self, stage: str, status: str, **detail: Any) -> None:
        event = {
            "stage": stage,
            "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
        logger.info("llm_stage stage=%s status=%s detail=%s", stage, status, detail)
        if self.progress_callback is not None:
            try:
                self.progress_callback(event)
            except Exception:  # A tracking failure must never break analysis.
                logger.exception("Progress callback failed for stage %s", stage)

    async def _run_stage(self, stage: str, coro: Any) -> Any:
        self._emit(stage, "running")
        try:
            result = await coro
        except Exception as exc:
            self._emit(stage, "failed", error=str(exc) or exc.__class__.__name__)
            raise
        self._emit(stage, "completed", **self.usage.stages.get(stage, {}))
        return result

    # ------------------------------------------------------------------
    # Individual stages
    # ------------------------------------------------------------------

    async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
        result = await self.client.generate_structured(
            instructions=EXTRACTION_PROMPT,
            input_text=_render_pages(data),
            output_schema=ExtractedInformation,
            cache_key=f"live-swot-extract-{PROMPT_VERSION}",
        )
        self.usage.record(
            "extract", result.input_tokens, result.output_tokens, result.cached_input_tokens
        )
        return result.output

    async def analyze_scadable(
        self, baseline: Mapping[str, Any], baseline_version: str
    ) -> CompanyAnalysis:
        memo_key = (baseline_version, PROMPT_VERSION, self.client.model)
        cached = _SCADABLE_CACHE.get(memo_key)
        if cached is not None:
            self.usage.record("scadable", 0, 0)
            return cached

        result = await self.client.generate_structured(
            instructions=SCADABLE_PROMPT,
            input_text=json.dumps(baseline, indent=2, sort_keys=True, default=str),
            output_schema=CompanyAnalysis,
            cache_key=f"live-swot-scadable-{PROMPT_VERSION}",
        )
        self.usage.record(
            "scadable", result.input_tokens, result.output_tokens, result.cached_input_tokens
        )
        _SCADABLE_CACHE[memo_key] = result.output
        return result.output

    async def compare(
        self,
        baseline: Mapping[str, Any],
        scadable: CompanyAnalysis,
        facts: ExtractedInformation,
        allowed_urls: list[str],
    ) -> ComparisonResult:
        input_text = "\n\n".join(
            [
                "<scadable_profile>\n"
                + json.dumps(baseline, indent=2, sort_keys=True, default=str)
                + "\n</scadable_profile>",
                "<scadable_analysis>\n" + scadable.model_dump_json(indent=2)
                + "\n</scadable_analysis>",
                "<competitor_facts>\n" + facts.model_dump_json(indent=2)
                + "\n</competitor_facts>",
                "<allowed_urls>\n" + "\n".join(allowed_urls) + "\n</allowed_urls>",
            ]
        )
        result = await self.client.generate_structured(
            instructions=COMPARISON_PROMPT,
            input_text=input_text,
            output_schema=ComparisonResult,
            cache_key=f"live-swot-compare-{PROMPT_VERSION}",
        )
        self.usage.record(
            "compare", result.input_tokens, result.output_tokens, result.cached_input_tokens
        )
        return result.output

    # ------------------------------------------------------------------
    # Cost guard
    # ------------------------------------------------------------------

    def estimate_run_cost(
        self, analysis_input: AnalysisInput, baseline: Mapping[str, Any]
    ) -> float | None:
        """Upper-bound USD estimate for one run, or None without pricing."""
        baseline_text = json.dumps(baseline, default=str)
        page_text = _render_pages(analysis_input)
        input_tokens = (
            estimate_tokens(EXTRACTION_PROMPT + page_text)
            + estimate_tokens(SCADABLE_PROMPT + baseline_text)
            + estimate_tokens(COMPARISON_PROMPT + baseline_text)
            + _ESTIMATED_OUTPUT_TOKENS["extract"]  # facts are fed into compare
            + _ESTIMATED_OUTPUT_TOKENS["scadable"]
        )
        output_tokens = sum(_ESTIMATED_OUTPUT_TOKENS.values())
        return compute_cost_usd(
            input_tokens,
            output_tokens,
            self.settings.llm_price_input_per_1m,
            self.settings.llm_price_output_per_1m,
        )

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def run(
        self,
        scraped_data: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Run every stage and return the orchestrator-facing result dict."""
        for stage in STAGES:
            self._emit(stage, "queued")

        company_name = str(scraped_data.get("competitor_name") or "Unknown").strip() or "Unknown"
        pages = prepare_pages(
            scraped_data,
            self.settings.llm_max_chars_per_page,
            self.settings.llm_max_total_chars,
        )
        if not pages:
            raise EmptyInputError(f"No page text to analyze for {company_name}.")

        analysis_input = AnalysisInput(company_name=company_name, pages=pages)
        versions = build_versions(scraped_data, baseline, self.client.model)

        estimate = self.estimate_run_cost(analysis_input, baseline)
        cap = self.settings.llm_max_cost_per_run_usd
        if cap is not None and estimate is not None and estimate > cap:
            raise CostLimitExceeded(
                f"Estimated cost ${estimate:.4f} exceeds LLM_MAX_COST_PER_RUN_USD=${cap:.4f}."
            )

        facts, scadable = await asyncio.gather(
            self._run_stage("extract", self.extract_information(analysis_input)),
            self._run_stage(
                "scadable", self.analyze_scadable(baseline, versions["baseline_version"])
            ),
        )

        crawled_urls = [p.url for p in pages]
        comparison: ComparisonResult = await self._run_stage(
            "compare", self.compare(baseline, scadable, facts, crawled_urls)
        )

        self._emit("validate", "running")
        result = self._assemble(
            company_name, pages, facts, scadable, comparison, versions, estimate
        )
        self._emit(
            "validate", "completed", warnings=len(result["warnings"]),
            findings=len(result["findings"]),
        )
        return result

    def _assemble(
        self,
        company_name: str,
        pages: list[PageInput],
        facts: ExtractedInformation,
        scadable: CompanyAnalysis,
        comparison: ComparisonResult,
        versions: dict[str, str],
        estimate: float | None,
    ) -> dict[str, Any]:
        url_index = build_url_index(p.url for p in pages)
        warnings: list[str] = []

        findings, finding_warnings = validate_findings(
            (f.model_dump() for f in comparison.swot), url_index
        )
        warnings.extend(finding_warnings)
        missing = {c for c in ("strength", "weakness", "opportunity", "threat")} - {
            f["category"] for f in findings
        }
        if missing:
            warnings.append(f"SWOT is missing categories: {sorted(missing)}")

        signals = []
        for signal in comparison.signals:
            data = signal.model_dump()
            data["source_urls"], dropped = filter_citations(data["source_urls"], url_index)
            if dropped:
                warnings.append(f"Dropped uncrawled citation(s) {dropped} from signal.")
            signals.append(data)

        profile = comparison.profile.model_dump()
        profile["source_urls"], _ = filter_citations(profile["source_urls"], url_index)

        fact_dicts = []
        for fact in facts.facts:
            data = fact.model_dump()
            valid, dropped = filter_citations([data["source_url"]], url_index)
            if dropped:
                warnings.append(f"Dropped extracted fact citing uncrawled URL {dropped[0]}.")
                continue
            data["source_url"] = valid[0]
            fact_dicts.append(data)

        for warning in warnings:
            logger.warning("LLM output validation (%s): %s", company_name, warning)

        return {
            # --- Backward-compatible keys consumed by the orchestrator ---
            "competitor_name": company_name,
            "summary": comparison.profile.summary or facts.summary,
            "swot_entries": to_swot_entries(findings),
            # --- Additive keys ---
            "analysis_mode": "real",
            "profile": profile,
            "signals": signals,
            "findings": findings,
            "facts": fact_dicts,
            "missing_topics": list(facts.missing_topics),
            "scadable_analysis": scadable.model_dump(),
            "sources": [{"url": p.url, "title": p.title} for p in pages],
            "versions": versions,
            "usage": {**self.usage.to_dict(), "preflight_estimate_usd": estimate},
            "warnings": warnings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
