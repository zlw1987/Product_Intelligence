"""Manual live-smoke check for the Serper adapter (PRODUCT-INTEL.2C).

Not part of the automated suite — `pyproject.toml` only collects `tests/`, and
this script lives outside it deliberately. Run it by hand, on purpose, when you
need to confirm the real Serper integration still works:

    python scripts/serper_live_smoke.py
    python scripts/serper_live_smoke.py "some other public part number"

It makes exactly one live call to Serper's ordinary Google Search endpoint per
invocation. It never prints, logs, or otherwise surfaces the API key — only a
safe summary: provider id, the query text, the result count, and each result's
public title and URL.

Requires `SERPER_API_KEY` in the process environment (see CLAUDE.md — never in
a repository file). If it is missing, this script says so and exits without
making a request.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product_intelligence.providers.search import SearchProviderError, SearchQuery
from product_intelligence.providers.serper import (
    SERPER_API_KEY_ENV_VAR,
    SerperSearchProvider,
)

#: A public REAL_VERIFIED MPN from evaluation/corpus/real_verified.json
#: (case REAL-0001), used only as a default — never a benchmark value baked
#: into production logic.
DEFAULT_QUERY_TEXT = "MZ-QL23T800"


def main(argv: list[str]) -> int:
    if SERPER_API_KEY_ENV_VAR not in os.environ:
        print(
            f"{SERPER_API_KEY_ENV_VAR} is not set in the environment; "
            "nothing was called."
        )
        return 1

    query_text = argv[1] if len(argv) > 1 else DEFAULT_QUERY_TEXT
    provider = SerperSearchProvider.from_environment()
    query = SearchQuery(text=query_text)

    try:
        response = provider.search(query)
    except SearchProviderError as exc:
        print(f"Serper search failed: {exc}")
        return 1

    print(f"provider_id: {response.provider_id}")
    print(f"query: {response.query.text}")
    print(f"retrieved_at: {response.retrieved_at.isoformat()}")
    print(f"result_count: {response.result_count}")
    for result in response.results:
        print(f" - {result.title!r} | {result.source_url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
