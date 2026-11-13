"""Default-provider entry for post-claim vendor-refresh execution
(VREF-R1-2, decision M2 / O9).

Thin command-stack entry: supplies the concrete
``InternalVendorAdapter`` CLASS as the zero-arg
``vendor_adapter_factory`` and delegates ONCE to
``execute_claimed_vendor_refresh``. This module is the ONLY R1 module
that imports ``providers.internal_vendor`` (function-level import —
DESIGN2 section 3.5 placement; AST-pinned by the R1-2 network
boundary suite). It constructs NOTHING itself: the single adapter
construction happens inside the execution core, at S7, strictly after
the state re-assert and all preflight checks (I13). This is the
recorded O9 deviation from ``comparable_runtime``'s eager
construction: R1's zero-construction guarantee (LB-3) on every
refusal and preflight branch requires the lazy factory form.

The full post-claim contract (argument discipline, [A] state
precondition, S4-S9 sequence, T1-T4 terminal-CAS outcomes, the scoped
LB-1 lookup guarantee and its direct-executor-reuse limit) is exactly
the execution core's — see ``vendor_refresh``'s module docstring.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotation only
    from product_intelligence.runs.models import VendorRefreshExecution

__all__ = [
    "execute_claimed_vendor_refresh_with_default_providers",
]


def execute_claimed_vendor_refresh_with_default_providers(
    child_id: uuid.UUID | str,
) -> "VendorRefreshExecution":
    """Execute one already-claimed RUNNING vendor-refresh child with
    the default (concrete internal Vendor) provider.

    Delegates once to ``execute_claimed_vendor_refresh`` with the
    concrete ``InternalVendorAdapter`` class as the factory. POST-
    CLAIM ONLY: nothing here claims, transitions PENDING -> RUNNING,
    or executes a PENDING or terminal child.

    Returns
    -------
    object
        The ``VendorRefreshExecution`` row the executor returns (the
        T1 durably stored terminal row, or the T2/T4 actual durable
        state established by the reconciliation fresh read).

    Raises
    ------
    VendorRefreshExecutionError
        The executor's bounded refusal / defect / T3-T4 outcomes.
    """
    from product_intelligence.execution.vendor_refresh import (
        execute_claimed_vendor_refresh,
    )
    from product_intelligence.providers.internal_vendor import (
        InternalVendorAdapter,
    )

    return execute_claimed_vendor_refresh(
        child_id,
        vendor_adapter_factory=InternalVendorAdapter,
    )
