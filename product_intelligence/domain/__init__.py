"""Domain contracts for Product Intelligence.

This package is deliberately framework-light and dependency-free:

* standard library only
* no Django imports
* no HTTP, no network access, no filesystem access
* no LLM calls
* no external search or LLM vendor names
* no concepts belonging to any specific calling system

Every supported intake mechanism must normalize into these types before the
research core sees the request. Caller metadata, transport details, and
encoding quirks belong at the intake/application boundary, never here.

Status: PRODUCT-INTEL.0A defines the contracts below. Behaviour that consumes
them (matching, pricing, evidence collection, persistence) is not implemented.
"""

from product_intelligence.domain.enums import (
    ESTABLISHED_MATCH_TYPES,
    ConfidenceLevel,
    EvidenceDecision,
    IdentityMatchType,
    ResearchRunState,
    VerificationStatus,
)
from product_intelligence.domain.errors import DomainValidationError
from product_intelligence.domain.models import (
    EvidenceReference,
    ProductIdentity,
    ResearchRequest,
)

__all__ = [
    "ESTABLISHED_MATCH_TYPES",
    "ConfidenceLevel",
    "DomainValidationError",
    "EvidenceDecision",
    "EvidenceReference",
    "IdentityMatchType",
    "ProductIdentity",
    "ResearchRequest",
    "ResearchRunState",
    "VerificationStatus",
]
