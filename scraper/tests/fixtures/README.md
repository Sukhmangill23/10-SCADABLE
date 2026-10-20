# Offline fixtures

All domains and content are synthetic. No fixture was captured from a competitor site.

- `pricing.html`: a short marketing page with a pricing table, meaningful query parameters,
  a tracking parameter, an internal product link and an external jobs link.
- `sitemap.xml`: a namespaced sitemap with eligible, excluded and external candidates.
- `crawl4ai_success.json`: a synthetic Crawl4AI 0.9.5 `CrawlResult`, populated through the
  installed SDK model and serialized with its supported fields/defaults. This models the
  SDK result shape for future mocked fetches, including Markdown variants and both link groups.

The SDK's deprecated top-level `fit_html` property cannot be dumped in JSON mode. That
deprecated field is omitted; its supported replacement is `markdown.fit_html`. Adapter
implementations should map documented SDK attributes to our application models rather
than dumping the entire SDK result to output. The fixture compatibility test checks the
Markdown and link shape against the actual installed SDK.
