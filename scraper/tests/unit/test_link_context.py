from scraper import FetchedPage
from scraper.decision_models import PageAssessment
from scraper.discovery.evidence import EvidenceLedger, link_observations
from scraper.models import DiscoveredLink
from scraper.types import utc_now


def page(html, links=(), **updates):
    return FetchedPage(
        source_url="https://example.com/",
        crawl_timestamp=utc_now(),
        crawl_status="success",
        raw_html=html,
        raw_markdown="# Company",
        links=[DiscoveredLink(url=url) for url in links],
        **updates,
    )


def test_context_uses_rendered_html_and_resolves_against_final_url():
    source = page(
        """<nav><a href="/atlas">Atlas</a></nav><main><section>
      <h2>Contract review</h2><p>Review agreements quickly. <a href="atlas#plans">Meet Atlas</a></p>
      </section></main><footer><a href="/atlas">Learn more</a></footer>
      <script>private script</script>""",
        ["https://example.com/atlas"],
        final_url="https://example.com/",
    )
    values = link_observations(source)
    observations = values["https://example.com/atlas"]
    assert len(observations) == 2
    main = next(item for item in observations if item.location == "main_content")
    assert main.heading == "Contract review"
    assert "Review agreements" in main.surrounding_text
    assert "private script" not in main.surrounding_text
    assert source.raw_html.startswith("<nav>")


def test_context_is_bounded_and_html_does_not_invent_links_missing_from_sdk():
    source = page(
        "<main><h1>"
        + "H" * 300
        + "</h1><p>"
        + "P" * 1000
        + '<a href="/atlas">'
        + "A" * 300
        + '</a></p><a href="/hidden">Other</a></main>',
        ["https://example.com/atlas"],
    )
    values = link_observations(source)
    assert set(values) == {"https://example.com/atlas"}
    item = values["https://example.com/atlas"][0]
    assert len(item.anchor_text) == 160
    assert len(item.heading) == 160
    assert 0 < len(item.surrounding_text) <= 400


def test_missing_html_uses_anchor_text_and_malformed_html_does_not_fail():
    source = page("")
    source = source.model_copy(
        update={"links": [DiscoveredLink(url="https://example.com/atlas", text="Meet Atlas")]}
    )
    assert link_observations(source)["https://example.com/atlas"][0].anchor_text == "Meet Atlas"
    assert link_observations(page("\x00<", ["https://example.com/atlas"]))


def test_ledger_retains_eight_useful_nonrepetitive_source_linked_excerpts():
    ledger = EvidenceLedger()
    for index in range(12):
        source = page("").model_copy(
            update={
                "source_url": f"https://example.com/{index}",
                "raw_markdown": f"Company evidence {index} " + "x" * 600,
                "content_assessment": PageAssessment(usefulness=index / 12, novelty=0.9),
            }
        )
        ledger.add(source)
    assert len(ledger.excerpts) == 8
    assert str(ledger.excerpts[0].source_url).endswith("/11")
    assert all(len(item.text) <= 500 for item in ledger.excerpts)
    prior = ledger.excerpts
    ledger.add(source.model_copy(update={"source_url": "https://example.com/duplicate"}))
    assert ledger.excerpts == prior


def test_ledger_samples_distinct_evidence_beyond_shared_navigation_prefix():
    ledger = EvidenceLedger()
    for index in range(8):
        source = page("").model_copy(
            update={
                "raw_markdown": "Navigation boilerplate " * 50 + f"Unique company evidence {index}",
                "content_assessment": PageAssessment(usefulness=0.9, novelty=0.9),
            }
        )
        ledger.add(source)
    assert len({item.text for item in ledger.excerpts}) == 8
    assert all("Unique company evidence" in item.text for item in ledger.excerpts)


def test_surrounding_context_is_near_the_anchor_in_a_long_container():
    source = page(
        "<main><p>"
        + "Industry filler " * 100
        + 'Legal contract review <a href="/atlas">Atlas</a> for law firms</p></main>',
        ["https://example.com/atlas"],
    )
    item = link_observations(source)["https://example.com/atlas"][0]
    assert "Legal contract review" in item.surrounding_text
    assert "Atlas" in item.surrounding_text
    assert "law firms" in item.surrounding_text
