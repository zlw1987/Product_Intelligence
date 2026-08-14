"""Web intake and presentation layer (Django).

This layer is the only place allowed to know about transports and callers:
form posts, URL parameters, character-encoding quirks, defensive parsing of
loosely-formed input, and redirects to a report URL. It converts all of that
into a ``product_intelligence.domain.ResearchRequest`` and hands it on.

Status: not implemented. The standalone research/report shell is
PRODUCT-INTEL.1B, the structured intake API is 5A, and the launcher-friendly
GET entry point is 5B. No views, templates, or routes exist yet.
"""
