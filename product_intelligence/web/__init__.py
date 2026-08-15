"""Web intake and presentation layer (Django).

This layer is the only place allowed to know about transports and callers:
form posts, URL parameters, character-encoding quirks, defensive parsing of
loosely-formed input, and redirects to a report URL. It converts all of that
into a ``product_intelligence.domain.ResearchRequest`` and hands it on.

Defensive parsing means *degrading honestly*, not recovering the unrecoverable.
A query string reserves characters — ``&`` starts the next parameter and ``#``
starts a fragment a browser normally never transmits — so a raw, unencoded
value containing them arrives already split or truncated. Constrained clients
percent-encode their values before launching the browser; raw values are
accepted best-effort for URL-safe characters only. This layer must never be
written, or documented, as though it could reconstruct bytes that never
reached it.

Status: not implemented. The standalone research/report shell is
PRODUCT-INTEL.1B, the structured intake API is 5A, and the launcher-friendly
GET entry point is 5B. No views, templates, or routes exist yet.
"""
