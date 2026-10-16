"""Conservative URL identity and exact-host scope, without making requests."""

from dataclasses import dataclass
from urllib.parse import unquote_plus, urljoin, urlsplit, urlunsplit

from pydantic import HttpUrl, ValidationError

from ..config import ScraperConfig

TRACKING_PARAMETERS = frozenset({"gclid", "dclid", "fbclid", "msclkid", "mc_cid", "mc_eid"})


@dataclass(frozen=True)
class NormalizedUrl:
    observed: str
    absolute: str
    normalized: str


def normalize_url(raw: str, *, base_url: str | None = None) -> NormalizedUrl | None:
    """Resolve HTTP(S) URLs, dropping fragments/tracking while keeping query bytes/order.

    Return None for invalid links. Credentials and control characters are never accepted.
    Path case, meaningful query order, repeated query keys and trailing slashes are retained.
    """
    if not raw or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return None
    try:
        url = HttpUrl(urljoin(base_url, raw.strip()) if base_url else raw.strip())
        if url.username is not None or url.password is not None:
            return None
        parts = urlsplit(str(url))
        host = parts.hostname.rstrip(".")
        host = f"[{host}]" if ":" in host else host
        netloc = f"{host}:{parts.port}" if parts.port else host
        query_parts = []
        for item in parts.query.split("&"):
            name = unquote_plus(item.split("=", 1)[0]).lower()
            if not name.startswith("utm_") and name not in TRACKING_PARAMETERS:
                query_parts.append(item)
        normalized = urlunsplit((parts.scheme, netloc, parts.path, "&".join(query_parts), ""))
        return NormalizedUrl(raw, str(url), normalized)
    except (ValidationError, ValueError):
        return None


class DomainScope:
    """The homepage host and its www alias, plus individually approved exact hosts.

    Crawl4AI's DomainFilter also allows subdomains. Exact matching here implements the
    deliberately narrower approved policy rather than silently enabling other subdomains.
    """

    def __init__(self, homepage: str, settings: ScraperConfig):
        normalized = normalize_url(homepage)
        if normalized is None:
            raise ValueError("A valid HTTP(S) homepage is required")
        host = urlsplit(normalized.normalized).hostname
        alias = host.removeprefix("www.") if host.startswith("www.") else f"www.{host}"
        self.allowed_hosts = frozenset((host, alias, *settings.allowed_domains))

    def allows(self, url: str) -> bool:
        normalized = normalize_url(url)
        return normalized is not None and (
            urlsplit(normalized.normalized).hostname in self.allowed_hosts
        )
