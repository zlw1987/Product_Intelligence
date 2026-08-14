"""Product Intelligence.

An independent web application that researches observable market pricing and
comparable products for a manufacturer part number (MPN) plus a product
description.

Package layout (see docs/PRODUCT_INTELLIGENCE_PLAN.md for the canonical design):

    domain/     Framework-light domain contracts. No web framework, no I/O,
                no external providers, no caller-specific concepts.
    research/   Research orchestration / core engine. Not implemented yet.
    providers/  Boundaries for external search and LLM providers.
                No real provider is integrated.
    web/        Django-facing presentation and intake layer.
                Not implemented yet.

Current phase: PRODUCT-INTEL.0A (architecture and domain contracts).
"""
