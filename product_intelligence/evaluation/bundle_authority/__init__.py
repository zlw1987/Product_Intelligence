"""FU4 Bundle authority qualification corpus family (Q3-C).

The separately versioned, independently labeled qualification corpus
family ``PI-FU4-BUNDLE-AUTHORITY-QUALIFICATION`` (design of record:
``docs/PRODUCT_INTEL_Q3C_FU4_BUNDLE_AUTHORITY_QUALIFICATION_DESIGN.md``).

This package is the ONLY home of the family (design section 3.3): it
reuses the frozen research public API and the semantic family's
patterns, and it never imports or modifies the byte-pinned
``product_intelligence/evaluation/semantic_v2`` harness.

C1 scope (design section 9.3): the strict corpus schema, the
constructor-as-validator decoder, the manifest integrity validator, the
builder skeleton, and the offline CLI. C1 creates NO qualification
cases, NO labels, NO evaluator, and NO capture. The expected label of
every future case remains an independently reviewed input — this
package never computes, completes, or upgrades one.
"""

__all__ = []
