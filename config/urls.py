"""Root URL configuration.

No routes are implemented in PRODUCT-INTEL.0A.

Planned entry points, recorded here so the URL shape is not re-invented later
(see docs/PRODUCT_INTELLIGENCE_PLAN.md):

* ``/research/new``            standalone web form            (1B)
* ``/research/<research-id>``  durable browser report          (1B)
* ``/api/v1/research``         structured intake for capable clients (5A)
* ``/research/new?mpn=...&description=...``
                              GET launcher entry point for constrained
                              legacy clients, tolerant of plain-text
                              parameters                        (5B)

None of these exist today.
"""

from __future__ import annotations

from django.urls.resolvers import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = []
