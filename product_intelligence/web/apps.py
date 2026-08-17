"""Django application configuration for the web intake/presentation layer.

The web layer is an application only so that its templates are discoverable and
its URLs have somewhere to live. It defines no model: a run outlives the request
that created it and belongs to no caller, so the lifecycle stays in
`product_intelligence.runs` (AD-025).
"""

from __future__ import annotations

from django.apps import AppConfig


class WebConfig(AppConfig):
    name = "product_intelligence.web"
    label = "web"
    verbose_name = "Web intake and reports"
