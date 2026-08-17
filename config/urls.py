"""Root URL configuration.

Implemented (PRODUCT-INTEL.1B), in `product_intelligence.web.urls`:

* ``/``                       redirect to the standalone form
* ``/research/new``           standalone web form
* ``/research/<research-id>`` durable browser report shell

The report is a *shell*: it displays the canonical request and the run's
lifecycle state. No research is executed, so a run stays in ``CREATED``.

Planned, recorded here so the URL shape is not re-invented later
(see docs/PRODUCT_INTELLIGENCE_PLAN.md):

* ``/api/v1/research``         structured intake for capable clients (5A)
* ``/research/new?mpn=<encoded>&description=<encoded>``
                              GET launcher entry point for constrained
                              legacy clients, which percent-encode their two
                              values before opening the browser. Raw values
                              are accepted best-effort for URL-safe
                              characters only — a query string cannot carry
                              arbitrary unencoded text losslessly     (5B)

Neither of those exists. A GET to ``/research/new`` displays the form and
creates nothing, whatever query parameters it carries.
"""

from __future__ import annotations

from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver
from django.views.generic import RedirectView

urlpatterns: list[URLPattern | URLResolver] = [
    # The standalone form is the whole application today, so the root address
    # leads to it rather than to a 404. It is a redirect, not a second route
    # serving the same page, so there is one canonical address for the form.
    path(
        "",
        RedirectView.as_view(pattern_name="research-new", permanent=False),
        name="root",
    ),
    path("", include("product_intelligence.web.urls")),
]
