"""Django application configuration for persisted research runs."""

from __future__ import annotations

from django.apps import AppConfig


class RunsConfig(AppConfig):
    name = "product_intelligence.runs"
    label = "runs"
    verbose_name = "Research runs"
