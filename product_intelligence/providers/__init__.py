"""External provider boundaries.

Two boundaries are planned:

    SearchProvider  -- finds candidate listings and pages
    LLMProvider     -- semantic assistance only (see the deterministic /
                       LLM split in docs/PRODUCT_INTELLIGENCE_PLAN.md)

Rules that hold from this phase onward:

* Business logic depends on the boundary, never on a specific vendor.
* Vendor names, request/response shapes, and credentials stay behind an
  adapter in this package and never reach the domain or the research core.
* Credentials are read from the server environment. No calling system ever
  supplies or holds them.

Status: not implemented. The abstraction is PRODUCT-INTEL.2B and the first
real search provider is 2C. No provider is integrated today.
"""
