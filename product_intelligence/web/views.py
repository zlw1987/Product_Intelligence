"""Standalone intake and report views (PRODUCT-INTEL.1B).

Two views, and between them the whole browser workflow that exists today:

```text
GET  /research/new      the form
POST /research/new      -> ResearchRequest -> ResearchRun (CREATED) -> redirect
GET  /research/<uuid>   the durable report shell
```

**No research happens here.** A submitted run is stored in `CREATED` and stays
there: nothing in this layer calls `transition_to`, because nothing exists to
move it — there is no search, no resolver, no pricing, and no background
processing. The report says so in those terms rather than showing a spinner.

The web layer owns transport and presentation only. It does not decide what a
valid request is (`ResearchRequest` does), and it does not decide how a run is
stored or advanced (`ResearchRun` does). It uses the supported creation API,
`ResearchRun.objects.create_from_request`, never a direct `create()`,
`bulk_create()`, `update()`, or raw SQL.
"""

from __future__ import annotations

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from product_intelligence.runs.models import ResearchRun
from product_intelligence.web.forms import ResearchRequestForm


def research_new(request: HttpRequest) -> HttpResponse:
    """Show the standalone intake form, and accept its submission.

    Post/Redirect/Get: a successful POST creates exactly one run and answers
    with a redirect, so reloading the report cannot submit anything a second
    time. An invalid POST re-renders the form with its errors and creates
    nothing.

    A GET is *always* a form display, even when query parameters are present.
    The launcher entry point that turns `?mpn=…&description=…` into a run is
    phase 5B and is deliberately not implemented here: making a GET create a
    record would mean a crawler, a prefetch, or a refresh silently starting
    research. Query parameters are ignored, not honoured, and not echoed.
    """
    if request.method == "POST":
        form = ResearchRequestForm(request.POST)
        if form.is_valid():
            run = ResearchRun.objects.create_from_request(form.research_request)
            return redirect("research-detail", run_id=run.id)
    else:
        form = ResearchRequestForm()

    return render(request, "web/research_new.html", {"form": form})


def research_detail(request: HttpRequest, run_id: uuid.UUID) -> HttpResponse:
    """The durable report shell for one run.

    Read-only in the strictest sense: it loads a row and renders it. It starts
    nothing, transitions nothing, and writes no timestamp — a report that
    advanced the thing it reports on would be a research trigger wearing a
    report's clothes.

    An unknown identifier is a 404. A malformed one never reaches this view at
    all: the URL converter refuses it, so the router answers 404 rather than the
    view raising on a bad UUID.

    The identifier in the URL is not a permission check. It resists enumeration
    and does nothing else; whether reports need authentication is still an open
    decision (§19 of the canonical plan), which is why this shell is not ready
    for deployment outside a trusted network.
    """
    run = get_object_or_404(ResearchRun, pk=run_id)

    return render(request, "web/research_detail.html", {"run": run})
