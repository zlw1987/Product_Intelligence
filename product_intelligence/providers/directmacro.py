"""DirectMacro adapter for direct-source location (PRODUCT-INTEL.4D-A).

4D-PRE proved that directmacro.com is the ONLY evidence-backed DIRECT source:

    Discovery = DIRECT_SITE
    Post-discovery = STATIC_PARTIAL

The site-owned search mechanism deterministically locates product pages from
an exact MPN via static HTTP:

    https://directmacro.com/catalogsearch/result/?q=<MPN>

This adapter implements ``DirectSourceLocator`` for DirectMacro. It:

* receives the exact requested MPN from a ``DirectSourceQuery``
* URL-encodes it correctly
* returns the DirectMacro search-results URL as a ``DirectSourceTarget``
* makes **NO** network call
* synthesises **NO** product-page slug
* parses **NO** identity
* maps **NO** SKU to MPN
* extracts **NO** price

The existing ``PageFetcher`` performs the actual HTTP acquisition later.

No DirectMacro logic belongs in ``research/``, ``web/``, or ``domain/``.
"""

from __future__ import annotations

from urllib.parse import quote

from product_intelligence.providers.direct_source import (
    DirectSourceLocator,
    DirectSourceQuery,
    DirectSourceTarget,
)

#: The base URL for DirectMacro's site-owned search mechanism.
#: Confirmed by 4D-PRE: ``action="https://directmacro.com/catalogsearch/result/"``,
#: ``input name=q``, ``method=get``.
_DIRECTMACRO_SEARCH_BASE = "https://directmacro.com/catalogsearch/result/?q="


class DirectMacroLocator:
    """``DirectSourceLocator`` for directmacro.com.

    Conforms to the protocol structurally — it inherits nothing and exposes
    only ``locate``. Makes zero network calls. URL-encodes the exact MPN
    into the known DirectMacro search endpoint.
    """

    def locate(self, query: DirectSourceQuery) -> tuple[DirectSourceTarget, ...]:
        """Return the DirectMacro search-results URL for the given MPN.

        Constructs one candidate target URL using the site-owned search
        mechanism proven by 4D-PRE. No network call is performed.
        """
        if not isinstance(query, DirectSourceQuery):
            raise TypeError(
                f"query must be a DirectSourceQuery, got {type(query).__name__}"
            )

        # URL-encode the exact MPN for the query parameter.
        # DirectMacro uses ``?q=<mpn>``; ``quote`` percent-encodes the value
        # so special characters in part numbers do not break the URL.
        # Alphanumeric and common part-number characters are safe in URLs.
        encoded_mpn = quote(query.manufacturer_part_number, safe="-_.~")
        search_url = f"{_DIRECTMACRO_SEARCH_BASE}{encoded_mpn}"

        return (DirectSourceTarget(url=search_url),)
