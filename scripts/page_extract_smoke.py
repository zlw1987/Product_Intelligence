"""Manual live-fetch and extraction check (PRODUCT-INTEL.3A).

Not part of the automated suite — `pyproject.toml` only collects `tests/`, and
this script lives outside it deliberately. Run it by hand, on purpose, against
one public product URL:

    python scripts/page_extract_smoke.py https://example.com/some-product

It performs **exactly one** bounded GET per invocation, through the same
`HttpPageFetcher` the tests exercise offline — same timeout, same redirect
limit, same response-size limit, same refusal of non-public destinations, same
absence of any credential — and then runs the same deterministic extractor over
what came back.

It prints a compact summary only: the requested and final URLs, the status, the
content type, the document size, and each raw observation's fields. It never
dumps the page, and there is nothing secret for it to leak — a page fetch is
anonymous, so no API key, cookie, or authorization header exists in this path.

It is not wired to Django, to a `ResearchRun`, or to the search provider. It
calls no external search service, so it consumes no search credits.
"""

from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product_intelligence.providers.http_page import HttpPageFetcher
from product_intelligence.providers.page import (
    PageFetchError,
    PageFetchRequest,
    UnsafeFetchTargetError,
)
from product_intelligence.research.extraction import extract_listing_observations

#: Long enough not to be a summary, short enough not to be a page dump.
MAX_VALUE_CHARACTERS = 120


def _shorten(value: str) -> str:
    if len(value) <= MAX_VALUE_CHARACTERS:
        return value
    return value[:MAX_VALUE_CHARACTERS] + f"... ({len(value)} chars)"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/page_extract_smoke.py <public-product-url>")
        return 2

    try:
        request = PageFetchRequest(argv[1])
    except (TypeError, ValueError) as exc:
        print(f"refused before fetching: {exc}")
        return 1

    try:
        page = HttpPageFetcher().fetch(request)
    except UnsafeFetchTargetError as exc:
        print(f"refused this destination: {exc}")
        return 1
    except PageFetchError as exc:
        print(f"fetch failed: {exc}")
        return 1

    print(f"requested : {page.requested_url}")
    print(f"final     : {page.final_url}")
    print(f"status    : {page.status_code}")
    print(f"type      : {page.content_type}")
    print(f"size      : {page.body_byte_count} bytes")
    print(f"redirects : {page.redirect_count}")
    print(f"fetcher   : {page.fetcher_id}")
    print(f"retrieved : {page.retrieved_at.isoformat()}")

    observations = extract_listing_observations(
        page.body_text, source_url=page.final_url
    )
    print(f"\nraw listing observations: {len(observations)}")

    if not observations:
        print(
            "  none — this page publishes no structured product data that this "
            "phase reads. That is a finding about the source, not a price of "
            "zero and not a reason to guess from visible text."
        )
        return 0

    skipped = {"source_url", "raw_reference"}
    for index, observation in enumerate(observations, start=1):
        print(f"\n  [{index}] via {observation.extraction_method.value}")
        for field in fields(observation):
            if field.name in skipped or field.name == "extraction_method":
                continue
            value = getattr(observation, field.name)
            if value is not None:
                print(f"      {field.name:32} {_shorten(value)}")

    print(
        "\nEvery value above is raw observed text. Nothing here is a market "
        "price, a normalized value, or an accepted listing."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
