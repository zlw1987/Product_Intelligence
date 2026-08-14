"""Research core.

This is where the caller-independent research engine will live: product
resolution, price intelligence, comparable-product research, evidence
handling, and the research-run lifecycle.

The engine consumes ``product_intelligence.domain.ResearchRequest`` and knows
nothing about how that request arrived.

Status: not implemented. The run lifecycle is PRODUCT-INTEL.1A; identity
matching is 2A; listing work is 3A-3C; pricing is 4A-4B; comparables are
7A-7C.
"""
