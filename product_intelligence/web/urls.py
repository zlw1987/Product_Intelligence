"""Routes for the standalone browser workflow (PRODUCT-INTEL.1B).

```text
/research/new       GET  the intake form
                    POST create one run, then redirect
/research/<uuid>    GET  the durable report shell
```

The URL shape is the one recorded in the canonical plan, so the launcher work
in 5B adds an adapter at this boundary rather than a second address for the
same thing. Nothing versioned is invented here: the structured API at
`/api/v1/research` is 5A's to define.

`<uuid:run_id>` is the 404 boundary for a malformed identifier — the converter
refuses anything that is not a UUID, so the router answers before a view can be
handed a value it would have to raise on.
"""

from __future__ import annotations

from django.urls import path

from product_intelligence.web import views

urlpatterns = [
    path("research/new", views.research_new, name="research-new"),
    path("research/<uuid:run_id>", views.research_detail, name="research-detail"),
    path("research/<uuid:run_id>/retry", views.research_retry, name="research-retry"),
]
