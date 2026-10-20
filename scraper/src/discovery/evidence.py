"""Network-free, bounded link context and source-linked content feedback."""

import hashlib

from lxml import etree, html

from ..decision_models import CandidateObservation, CollectedExcerpt
from ..decision_prompts import sample_markdown
from ..models import FetchedPage
from .urls import normalize_url

_LOCATIONS = {"main_content": 0, "navigation": 1, "unknown": 2, "footer": 3}
_CONTAINERS = {"section", "article", "div", "main", "nav", "footer", "body"}


def bounded_observations(items) -> list[CandidateObservation]:
    distinct = []
    for item in items:
        item = item.model_copy(
            update={
                key: " ".join(getattr(item, key).split())
                for key in ("anchor_text", "heading", "surrounding_text")
            }
        )
        if item not in distinct:
            distinct.append(item)
    return sorted(
        distinct,
        key=lambda item: (
            _LOCATIONS[item.location],
            -len(item.surrounding_text),
            -len(item.anchor_text),
            -len(item.heading),
        ),
    )[:2]


def _text(node, limit):
    parts = []
    size = 0
    for text in node.itertext():
        text = " ".join(text.split())
        if text:
            part = text[: max(0, limit - size)]
            parts.append(part)
            size += len(part) + 1
            if size >= limit:
                break
    return " ".join(parts)[:limit]


def _surrounding(parent, anchor, limit=400):
    """Keep a bounded text window before and after this exact anchor node."""
    before = ""
    after = ""
    found = False
    for event, node in etree.iterwalk(parent, events=("start", "end")):
        if event == "start" and node is anchor:
            found = True
        text = node.text if event == "start" else (node.tail if node is not parent else None)
        if not text:
            continue
        text = " ".join(text.split())
        if not found:
            before = (before + " " + text)[-(limit // 2) :]
        else:
            remaining = limit - len(before) - len(after) - 1
            after += (" " + text)[: max(0, remaining)]
            if len(before) + len(after) + 1 >= limit:
                break
    return (before + " " + after).strip()[:limit]


def link_observations(page: FetchedPage) -> dict[str, list[CandidateObservation]]:
    """Enrich SDK-discovered links only; parsing HTML never creates new fetches."""
    base = str(page.final_url or page.source_url)
    values = {}
    for link in page.links:
        normalized = normalize_url(str(link.url), base_url=base)
        if normalized is None:
            continue
        key = normalized.normalized
        values.setdefault(key, [])
        text = " ".join((link.text or link.title or "").split())[:160]
        if text:
            values[key] = bounded_observations(
                [
                    *values[key],
                    CandidateObservation(
                        parent_url=base,
                        anchor_text=text,
                    ),
                ]
            )
    if not page.raw_html or not values:
        return values
    try:
        document = html.document_fromstring(
            page.raw_html.encode("utf-8"),
            parser=html.HTMLParser(
                encoding="utf-8",
                no_network=True,
                recover=True,
            ),
        )
    except (etree.ParserError, etree.XMLSyntaxError, ValueError):
        return values
    for node in document.xpath("//script | //style | //noscript | //template | //head"):
        node.drop_tree()
    headings = {}
    for node in document.iter():
        if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            container = next(
                (item for item in node.iterancestors() if item.tag in _CONTAINERS), document
            )
            headings[container] = _text(node, 160)
        if node.tag != "a" or not node.get("href"):
            continue
        normalized = normalize_url(node.get("href"), base_url=base)
        if normalized is None or normalized.normalized not in values:
            continue
        ancestors = list(node.iterancestors())
        location = "unknown"
        for ancestor in ancestors:
            role = ancestor.get("role")
            if ancestor.tag == "nav" or role == "navigation":
                location = "navigation"
                break
            if ancestor.tag == "footer" or role == "contentinfo":
                location = "footer"
                break
            if ancestor.tag in {"main", "article"} or role == "main":
                location = "main_content"
                break
        parent = next((item for item in ancestors if item.tag in _CONTAINERS | {"p", "li"}), node)
        observation = CandidateObservation(
            parent_url=base,
            anchor_text=_text(node, 160) or (node.get("title") or "")[:160],
            heading=next((headings[item] for item in ancestors if item in headings), ""),
            surrounding_text=_surrounding(parent, node),
            location=location,
        )
        key = normalized.normalized
        values[key] = bounded_observations([*values[key], observation])
    return values


class EvidenceLedger:
    """Keep eight distinct, useful/nonrepetitive excerpts without retaining page bodies."""

    def __init__(self):
        self._entries = []

    @property
    def excerpts(self) -> list[CollectedExcerpt]:
        return [entry[2] for entry in self._entries]

    def add(self, page: FetchedPage) -> None:
        assessment = page.content_assessment
        if page.crawl_status != "success" or assessment is None:
            return
        value = (assessment.usefulness or 0) * (assessment.novelty or 0)
        text = sample_markdown(" ".join(page.raw_markdown.split()), limit=500)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if not text or value <= 0 or any(entry[1] == digest for entry in self._entries):
            return
        self._entries.append(
            (
                value,
                digest,
                CollectedExcerpt(
                    source_url=page.final_url or page.source_url,
                    text=text,
                    page_title=(page.page_title or "")[:160],
                ),
            )
        )
        self._entries.sort(key=lambda entry: -entry[0])
        del self._entries[8:]
