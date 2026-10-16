"""Bounded sitemap and sitemap-index discovery; candidate pages are never probed."""

import asyncio
import gzip
import zlib
from collections import deque
from io import BytesIO
from urllib.parse import urljoin
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ..config import ScraperConfig
from ..interfaces import DiscoveryBatch
from ..models import DiscoveredUrl
from ..types import WebUrl
from .http import GuardedHttpClient, RequestBlocked
from .urls import normalize_url


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _locations(root):
    for entry in root:
        for child in entry:
            if _local_name(child.tag) == "loc" and child.text:
                yield child.text.strip()


class BoundedSitemapDiscoverer:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def discover(self, homepage: WebUrl | str, settings: ScraperConfig) -> DiscoveryBatch:
        urls: dict[str, DiscoveredUrl] = {}
        warnings: list[str] = []
        truncated = False
        async with GuardedHttpClient(str(homepage), settings, transport=self._transport) as client:
            try:
                async with asyncio.timeout(settings.discovery_timeout_seconds):
                    rules = await client.robots_for(str(homepage))
                    roots = list(rules.sitemaps)
                    roots = [
                        *roots,
                        urljoin(str(homepage), "/sitemap.xml"),
                        urljoin(str(homepage), "/sitemap_index.xml"),
                    ]
                    roots = list(dict.fromkeys(roots))
                    queue = deque((root, 0) for root in roots[: settings.max_sitemap_documents])
                    truncated |= len(roots) > settings.max_sitemap_documents
                    seen: set[str] = set()
                    documents = 0
                    while queue:
                        target, depth = queue.popleft()
                        normalized = normalize_url(target, base_url=str(homepage))
                        if normalized is None:
                            warnings.append("invalid_sitemap_url")
                            continue
                        target = normalized.normalized
                        if target in seen:
                            continue
                        seen.add(target)
                        if depth > settings.max_sitemap_depth:
                            truncated = True
                            warnings.append(f"sitemap_depth_limit: {target}")
                            continue
                        if documents >= settings.max_sitemap_documents:
                            truncated = True
                            warnings.append("sitemap_document_limit")
                            break
                        documents += 1
                        try:
                            document = await client.document(target)
                            if document.status in (404, 410):
                                continue
                            if document.status != 200:
                                warnings.append(f"sitemap_http_{document.status}: {target}")
                                continue
                            content = document.body
                            if content.startswith(b"\x1f\x8b"):
                                with gzip.GzipFile(fileobj=BytesIO(content)) as stream:
                                    content = stream.read(settings.max_sitemap_bytes + 1)
                                if len(content) > settings.max_sitemap_bytes:
                                    raise RequestBlocked("response_too_large", target)
                            root = ElementTree.fromstring(content, forbid_dtd=True)
                            kind = _local_name(root.tag)
                            if kind not in ("sitemapindex", "urlset"):
                                warnings.append(f"unsupported_sitemap_format: {target}")
                                continue
                            child_documents = []
                            for location in _locations(root):
                                candidate = normalize_url(location, base_url=document.url)
                                if candidate is None:
                                    warnings.append("invalid_sitemap_entry")
                                    continue
                                if kind == "sitemapindex":
                                    if candidate.normalized in seen:
                                        continue
                                    if len(child_documents) < settings.max_sitemap_documents:
                                        child_documents.append((candidate.normalized, depth + 1))
                                    else:
                                        truncated = True
                                    continue
                                key = candidate.normalized
                                if key in urls:
                                    continue
                                if len(urls) >= settings.max_discovered_urls:
                                    truncated = True
                                    break
                                urls[key] = DiscoveredUrl(
                                    url=candidate.absolute,
                                    normalized_url=key,
                                    discovery_source="sitemap",
                                    parent_url=document.url,
                                    depth=1,
                                    depth_basis="sitemap_seed",
                                )
                            # Index references are stronger evidence than speculative root
                            # fallbacks. Preserve their source order while bounding the queue.
                            for child in reversed(child_documents):
                                queue.appendleft(child)
                                if len(queue) > settings.max_sitemap_documents:
                                    queue.pop()
                                    truncated = True
                            if truncated and len(urls) >= settings.max_discovered_urls:
                                break
                        except RequestBlocked as error:
                            warnings.append(str(error))
                            if error.reason in ("sitemap_request_limit", "response_too_large"):
                                truncated = True
                        except (
                            ParseError,
                            DefusedXmlException,
                            OSError,
                            EOFError,
                            zlib.error,
                        ) as error:
                            warnings.append(f"invalid_sitemap: {target}: {type(error).__name__}")
            except TimeoutError:
                truncated = True
                warnings.append("sitemap_discovery_timeout")
            except RequestBlocked as error:
                warnings.append(str(error))
        return DiscoveryBatch(
            urls=list(urls.values()), truncated=truncated, warnings=list(dict.fromkeys(warnings))
        )
