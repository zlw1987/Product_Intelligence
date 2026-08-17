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

Status (PRODUCT-INTEL.1B): the standalone research/report shell is
implemented — a form at ``/research/new``, a durable report at
``/research/<id>``, and the ``ResearchRequest`` translation between them. It
records a run; **it executes no research**, because no research capability
exists. The structured intake API is 5A, and the launcher-friendly GET entry
point is 5B; neither exists, and a GET to ``/research/new`` carrying query
parameters is a form display, never a submission.

This package owns no model. Persistence is ``product_intelligence.runs``.
"""
