"""Provider-neutral boundary for direct-source product location (PRODUCT-INTEL.4D-A).

This module defines the generic, vendor-free contracts used to locate a product
page directly from a manufacturer part number, without external search.

```text
DirectSourceQuery  ->  DirectSourceLocator.locate(query)  ->  DirectSourceTarget, ...
```

What this boundary is *not*
----------------------------

**It is not acquisition.** No HTTP call is performed here. The targets are
candidate URLs for later retrieval by whatever `PageFetcher` the orchestration
layer uses.

**It is not identity.** A `DirectSourceTarget` is not verified, matched, or
accepted. It is one candidate URL that *may* contain evidence about the
requested part number. Identity is decided by frozen 3C, not by a locator.

**It is not a registry.** There is no plugin system, no dynamic provider
registry, no DI container, and no provider manager. A narrow static
configuration resolver enables the one evidence-backed direct adapter.

**It is not a crawler.** No link traversal, no sitemap, no queue, no frontier.
One query names one part number, and a locator returns zero or more candidate
URLs — not their links, frames, or assets.

Rules
-----

* Standard library only. No vendor SDK, no HTTP client, no Django, no model.
* Vendor-free. No vendor name appears in this module; that belongs only in
  the adapter module.
* Network-free. No socket, no DNS, no request. Location is URL construction.
* Research-free. No import of `product_intelligence.research`.
* Persistence-free. No database, no model, no migration.

Binding: the generic boundary stays exactly as clean as the search boundary
it models after. A guard test enforces this structurally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from product_intelligence.providers.page import require_fetchable_url


# ---------------------------------------------------------------------------
# Query contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirectSourceQuery:
    """One concrete direct-source location request.

    Carries the exact requested manufacturer part number. The locator uses
    this to construct candidate product-page or search-results URLs for a
    specific preferred source.

    Contract: ``manufacturer_part_number`` is a string, surrounding
    whitespace is removed, and what remains must be non-empty.
    """

    manufacturer_part_number: str

    def __post_init__(self) -> None:
        if not isinstance(self.manufacturer_part_number, str):
            raise TypeError(
                "manufacturer_part_number must be a string, got "
                f"{type(self.manufacturer_part_number).__name__}"
            )
        stripped = self.manufacturer_part_number.strip()
        if not stripped:
            raise ValueError(
                "manufacturer_part_number is required; a direct-source query "
                "with no part number has nothing to locate"
            )
        object.__setattr__(self, "manufacturer_part_number", stripped)


# ---------------------------------------------------------------------------
# Target contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DirectSourceTarget:
    """One candidate URL produced by a direct-source locator.

    ``url`` is a safe absolute ``http(s)`` URL that *may* contain evidence
    about the requested product. It is NOT verified, matched, or accepted.

    This is LOCATION only — it says nothing about price, condition,
    availability, or identity authority.

    Contract: ``url`` is validated by ``require_fetchable_url`` so it is an
    absolute, credential-free ``http(s)`` URL with a host present.
    """

    url: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "url", require_fetchable_url(self.url, "url")
        )


# ---------------------------------------------------------------------------
# Locator protocol
# ---------------------------------------------------------------------------


class DirectSourceLocator(Protocol):
    """The boundary the orchestration layer depends on for direct-source
    location.

    One synchronous method. A ``Protocol`` rather than a base class, so an
    adapter (or a test fake) conforms by shape and inherits nothing.

    An implementation is expected to:

    * accept a ``DirectSourceQuery`` and return zero or more
      ``DirectSourceTarget`` values;
    * make **no** network call — it constructs URLs from known structure;
    * synthesise no product-page slug — the returned URL points at a
      search-results or catalog page, not a fabricated product URL;
    * decide nothing about identity, price, or whether a target is a listing.
    """

    def locate(self, query: DirectSourceQuery) -> tuple[DirectSourceTarget, ...]:
        """Return candidate URLs for the requested part number.

        Returns an empty tuple if the source has no known mechanism for the
        given part number. Never raises for a missing product — zero targets
        is a valid answer.
        """
        ...
