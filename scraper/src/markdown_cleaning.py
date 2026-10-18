"""Prepare a separate HTML copy for Markdown, without modifying discovery evidence."""

import logging
from collections.abc import Sequence

from cssselect import ExpressionError
from lxml import etree, html
from lxml.cssselect import CSSSelector, LxmlHTMLTranslator

_CONTENT_CONTAINERS = {"main", "article", "section", "aside"}
logger = logging.getLogger(__name__)


class _HtmlSelectorTranslator(LxmlHTMLTranslator):
    """HTML parsing has no named XML namespaces; reject them during translation."""

    def xpath_element(self, selector):
        if selector.namespace not in {None, "", "*"}:
            raise ExpressionError("Named CSS namespaces are not supported for HTML cleanup")
        return super().xpath_element(selector)

    def xpath_attrib(self, selector):
        if selector.namespace not in {None, "", "*"}:
            raise ExpressionError("Named CSS namespaces are not supported for HTML cleanup")
        return super().xpath_attrib(selector)


def compile_markdown_selector(selector: str) -> CSSSelector:
    return CSSSelector(selector, translator=_HtmlSelectorTranslator())


def _is_site_chrome(node) -> bool:
    if not isinstance(node.tag, str) or node.tag in {"html", "body"}:
        return False
    roles = set(node.get("role", "").lower().split())
    if node.tag == "nav" or "navigation" in roles:
        return True
    # Page/article introductions and attribution are content, not site chrome.
    scoped = node.tag in _CONTENT_CONTAINERS or any(
        ancestor.tag in _CONTENT_CONTAINERS or "main" in ancestor.get("role", "").lower().split()
        for ancestor in node.iterancestors()
    )
    return not scoped and (node.tag == "footer" or bool(roles & {"banner", "contentinfo"}))


def prepare_markdown_html(
    source: str,
    *,
    remove_navigation_and_footer: bool = True,
    excluded_selectors: Sequence[str] = (),
) -> str:
    """Remove semantic site chrome and explicit CSS matches, preserving adjacent text.

    Never searches for menu/footer words in prose or guesses CSS class names. A
    document that cannot be parsed falls back to its original input.
    """
    if not source.strip() or (not remove_navigation_and_footer and not excluded_selectors):
        return source
    parser = html.HTMLParser(encoding="utf-8", no_network=True, recover=True)
    try:
        document = html.document_fromstring(
            source.encode("utf-8"),
            parser=parser,
        )
    except (etree.ParserError, etree.XMLSyntaxError):
        return source
    # Recovery can return a truncated tree without raising on parser resource limits.
    if any(error.level >= etree.ErrorLevels.FATAL for error in parser.error_log):
        logger.warning("Markdown cleanup skipped after fatal HTML parser recovery; source retained")
        return source
    matches = set()
    if remove_navigation_and_footer:
        matches.update(node for node in document.iter() if _is_site_chrome(node))
    for selector in excluded_selectors:
        matches.update(compile_markdown_selector(selector)(document))
    if document in matches:
        return ""
    # Skip children of already-excluded containers; drop_tree retains each outer tail.
    for node in matches:
        if node.getparent() is not None and not any(
            ancestor in matches for ancestor in node.iterancestors()
        ):
            node.drop_tree()
    return html.tostring(document, encoding="unicode", method="html")
