"""Preferred-source configuration resolver (PRODUCT-INTEL.4D-A).

Resolves the ``PI_PREFERRED_SEARCH_DOMAINS`` server environment variable into
the set of domains that have evidence-backed direct-source locators.

This module reads the server environment — a provider/execution boundary
concern. The generic contracts and research core read no configuration.

Rules
-----

* ``PI_PREFERRED_SEARCH_DOMAINS`` is a comma-separated list of domain names.
* Missing or empty configuration: no direct source acquisition (old behavior).
* Only evidence-backed domains activate their locators. Unsupported domains
  are silently ignored in this phase.
* Domain names are normalised to lowercase and stripped of whitespace.
* The resolver is a pure function of the configuration string, making it
  testable without environment manipulation.

Current evidence-backed domains:

  - ``directmacro.com`` — DirectMacroLocator (4D-PRE DIRECT)

Not implemented in this phase:

  - ``esaitech.com`` — SERPER_FALLBACK only (no direct adapter)
  - All UNSUITABLE domains — blocked
  - All INSUFFICIENT_EVIDENCE domains — insufficient evidence
"""

from __future__ import annotations

import os

# The environment variable ordinary operation reads the configuration from.
_PREFERRED_DOMAINS_ENV_VAR = "PI_PREFERRED_SEARCH_DOMAINS"

# Domains with evidence-backed direct-source locators (4D-PRE DIRECT only).
# A domain not in this set is silently ignored — it does not activate a
# locator and does not suppress fallback search.
_DIRECT_DOMAINS: frozenset[str] = frozenset({"directmacro.com"})


def resolve_preferred_domains() -> frozenset[str]:
    """Read the preferred-source configuration and return enabled domains.

    Returns a frozenset of domain names that have active direct-source
    locators. If the environment variable is missing or empty, returns an
    empty frozenset (preserving old behaviour: no direct acquisition).

    Only evidence-backed DIRECT domains activate their locators. Other
    domains (SERPER_FALLBACK, UNSUITABLE, INSUFFICIENT_EVIDENCE) are not
    activated and are silently filtered out.
    """
    raw = os.environ.get(_PREFERRED_DOMAINS_ENV_VAR)
    if not raw or not raw.strip():
        return frozenset()

    raw_domains = {d.strip().lower() for d in raw.split(",") if d.strip()}
    return raw_domains & _DIRECT_DOMAINS


def is_directmacro_enabled() -> bool:
    """Return True if DirectMacro direct acquisition is enabled."""
    return "directmacro.com" in resolve_preferred_domains()
