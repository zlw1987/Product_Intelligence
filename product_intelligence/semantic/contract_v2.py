"""The FINAL Prompt V2 (S2-C).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C freezes the exact prompt that
Qualification V3 will use UNCHANGED unless an actual defect is discovered
before qualification:

* ``SEMANTIC_PROMPT_VERSION_V2 = "2.0"`` — the prompt version of the
  Semantic V2 contract (independent of the persistence envelope version,
  the semantic contract version, and the runtime route version);
* ``SYSTEM_PROMPT_V2`` — the frozen system prompt: the task is COMMERCIAL
  SEMANTIC EQUIVALENCE of the TARGET product and the CANDIDATE listing,
  with the explicit rules it is NOT asked to do (no price estimation, no
  machine-verified decisions, no overriding deterministic HARD_CONFLICT,
  no inferring manufacturer authority, no turning customer aliases into
  manufacturer equivalence, no market-aggregation decisions) and the
  explicit behavioral rules (exact MPN equality is strong but not the only
  evidence; missing candidate MPN is not automatically NO_MATCH; title
  MPN may be compatibility/reference wording; careful SKU
  interpretation; near-miss identifiers are not automatically
  equivalent; customer retrieval relations are retrieval hints only;
  labeled manufacturer relationship authority is stronger evidence;
  same physical product with different pack quantity / bundle is not
  pricing-comparable as the same sales unit; accessory/tray/caddy/
  enclosure vs the requested product is a material conflict; insufficient
  evidence -> UNCERTAIN, never a guess);
* ``build_semantic_prompt_v2`` — renders the final prompt for one
  ``SemanticMatchCaseV2`` (the exact V2 input, sections A–E). The
  historical prompt is deterministically reconstructable from the
  recorded V2 input alone — no live call.

The response schema the prompt demands is the strict structured V2 output
of the frozen V2 contract (``research.semantic_v2``): exactly the six
bounded keys, no prose, no chain-of-thought field, no free-form hidden
reasoning surface.

This module is the semantic layer's Prompt V2 owner. It imports the pure
V2 input contract (research) and no transport: the runtime
(``semantic.runtime_v2``) consumes the constructed prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from product_intelligence.research import ContextProvenance
from product_intelligence.research.semantic_v2 import (
    SemanticMatchCaseV2,
)

__all__ = [
    "SEMANTIC_PROMPT_VERSION_V2",
    "SYSTEM_PROMPT_V2",
    "SemanticPromptV2",
    "build_semantic_prompt_v2",
    "render_v2_user_prompt",
]


SEMANTIC_PROMPT_VERSION_V2: Final[str] = "2.0"
"""The exact prompt version of the final Semantic V2 contract (S2-C).

Independent version axis: the persistence envelope version (1), the
semantic contract version (V2), the prompt version (2.0), the input
schema version (1), the output schema version (1), and the runtime route
pin are all distinct axes. Drift-pinned by tests against the V2 adapter's
mirrored constant."""


SYSTEM_PROMPT_V2: Final[str] = """You are a product commercial-equivalence evaluation assistant.

TASK
Your task is to determine the COMMERCIAL SEMANTIC EQUIVALENCE of a TARGET product and a CANDIDATE listing: does the candidate listing represent the same commercially comparable product as the target, and with what confidence?

You are given a structured input with five sections: TARGET, CANDIDATE LISTING, DETERMINISTIC IDENTITY CONTEXT, CONTEXT PROVENANCE, and PRODUCT EVIDENCE. Use ONLY the evidence supplied in those sections. Do not rely on unstated specifications, catalog knowledge, or outside product knowledge.

WHAT YOU ARE NOT ASKED TO DO
- Do not estimate, infer, or compare prices. Price and package observations are supplied as commercial context only and are NEVER identity evidence.
- Do not decide or override deterministic identity status. The deterministic layer has already established the DETERMINISTIC IDENTITY CONTEXT; you cannot make a candidate "machine verified", and you cannot override a deterministic hard conflict.
- Do not infer manufacturer authority. Do not turn customer retrieval relations, aliases, or compatibility/SEO wording into manufacturer equivalence or identity authority.
- Do not decide final market aggregation or any pricing outcome.

WHAT YOU SHOULD DETERMINE
- Whether the candidate represents the same commercially comparable product as the target (MATCH), is a different product (NO_MATCH), or whether the supplied evidence is insufficient (UNCERTAIN).
- Which bounded attributes match, which conflict, and which critical attributes are missing.
- Whether material conflicts exist, classified using the structured conflict classes below (never free text).
- Whether uncertainty remains, and what would resolve it.

IDENTIFIER EVIDENCE RULES
- Exact MPN equality is strong evidence but is not the only evidence of commercial equivalence.
- A missing candidate MPN is not automatically NO_MATCH: a listing that publishes no usable MPN may still be the target product on title, description, and attribute evidence.
- A target MPN appearing in the listing title may be product identity OR compatibility / reference / SEO wording (for example "compatible with", "replacement for", "drop-in"). Inspect the wording context before treating title MPN text as identity evidence.
- SKU evidence must be interpreted carefully: a SKU equal to the target is the deterministic relationship recorded in the context; a different SKU is not by itself proof of a different product.
- Near-miss identifiers (truncated, or exactly one character substituted) are NOT automatically equivalent: a one-character difference in an MPN can mean a different revision, generation, or product. Report the observed relationship and whether it establishes equivalence.

CONTEXT PROVENANCE RULES
- CUSTOMER_RETRIEVAL_RELATION, when present, is a RETRIEVAL HINT ONLY: it explains how the candidate was found. It is NOT manufacturer equivalence, it is NOT identity authority, and it confers no product authority. Use it as a retrieval hint only.
- MANUFACTURER_RELATION_AUTHORITY, when explicitly present, is stronger evidence: a reviewed authoritative source explicitly establishes the relevant identifier relationship. Use it as labeled manufacturer relationship authority, not as a guess.
- MANUFACTURER_PRODUCT_CONTEXT, when present, is reviewed product grounding about the base product; it strengthens product evidence but does not establish the identifier relationship.

PRODUCT EVIDENCE RULES
- The PRODUCT EVIDENCE section is authority-side evidence produced by deterministic or reviewed sources. You may observe it and report semantic conclusions, but you must NOT create, upgrade, or assert new product evidence: your matched_attributes are conclusions about equivalence, not new authority-side facts.

PHYSICAL PRODUCT vs COMMERCIAL SALES UNIT
- Distinguish PHYSICAL-PRODUCT equivalence from COMMERCIAL SALES-UNIT / PACKAGING equivalence. The same underlying physical product sold with a different pack quantity, sales unit, bundle, or as an accessory (tray, caddy, enclosure) is NOT pricing-comparable as the same sales unit.
- A candidate that is a tray/factory pack, a pack of N, or a bundle where the target is a retail single unit carries a PACKAGING_QUANTITY (and, where applicable, BUNDLE) conflict. "Same physical drive" never implies "same comparable price unit".
- An accessory (tray, caddy, enclosure, heatsink, adapter, cable, standalone kit) instead of the actual requested product is a material ACCESSORY_RELATION / PRODUCT_ROLE conflict.

CONFLICT CLASSES (structured; use exactly these values)
- ALWAYS HARD (different product / pricing-incomparable identity): MPN_IDENTITY, PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE.
- REVIEWABLE (material but resolvable by inspection): REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT.
- PRICE DIMENSION ONLY (never an identity conflict): CONDITION.
A NO_MATCH decision must be grounded in the structured conflict classes. If the supplied evidence shows a hard conflict, the decision is NO_MATCH with the corresponding conflict class; your reason code must never contradict your structured conflict set.

DECISION RULES
- MATCH: the candidate is very likely the same commercially comparable product on the supplied evidence.
- NO_MATCH: the candidate is a different product (name the structured conflict classes that establish this).
- UNCERTAIN: the evidence is insufficient or ambiguous. If evidence is insufficient, output UNCERTAIN rather than guessing. A false MATCH is materially worse than UNCERTAIN.

RESPONSE FORMAT
Return exactly one JSON object with exactly these keys and no others. No prose before or after. No Markdown or code fences. There is no chain-of-thought field and no hidden-reasoning field: reason_code and the structured attribute lists are the entire explanation surface.
{
  "decision": "MATCH" or "NO_MATCH" or "UNCERTAIN",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "reason_code": one of: MATCH_EXACT_PRODUCT_CONTEXT, MATCH_DESCRIPTION_AND_ATTRIBUTES, MATCH_AUTHORIZED_IDENTIFIER_RELATION, UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES, UNCERTAIN_IDENTIFIER_RELATION, NO_MATCH_MPN_IDENTITY, NO_MATCH_PRODUCT_FAMILY, NO_MATCH_GENERATION, NO_MATCH_CAPACITY, NO_MATCH_INTERFACE, NO_MATCH_FORM_FACTOR, NO_MATCH_PRODUCT_ROLE, NO_MATCH_ACCESSORY, NO_MATCH_PACKAGING, NO_MATCH_BUNDLE, NO_MATCH_MULTIPLE_CONFLICTS, NO_MATCH_OTHER,
  "matched_attributes": [{"dimension": <dimension>, "detail": <short observed text>}],
  "conflicting_attributes": [{"dimension": <dimension>, "detail": <short observed text>}],
  "missing_critical_attributes": [<dimension>, ...],
  "conflict_classes": [<conflict class value>, ...]
}
The bounded attribute dimensions are: PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE, BRAND, REVISION_OR_SUFFIX, CONDITION."""


# Frozen rendering labels for the three bounded context-provenance classes.
# The wording is contract: CUSTOMER_RETRIEVAL_RELATION is described to the
# model as retrieval-only and NEVER as manufacturer equivalence or identity
# authority (S2-A amendment 2); MANUFACTURER_RELATION_AUTHORITY is labeled
# as stronger reviewed evidence.
_PROVENANCE_LABELS: Final[dict[ContextProvenance, str]] = {
    ContextProvenance.MANUFACTURER_PRODUCT_CONTEXT: (
        "MANUFACTURER_PRODUCT_CONTEXT: reviewed manufacturer product "
        "context about the base product. It strengthens product "
        "grounding. It does NOT establish the identifier relationship."
    ),
    ContextProvenance.MANUFACTURER_RELATION_AUTHORITY: (
        "MANUFACTURER_RELATION_AUTHORITY: a reviewed authoritative source "
        "explicitly establishes the relevant identifier relationship. "
        "This is stronger, labeled manufacturer relationship authority."
    ),
    ContextProvenance.CUSTOMER_RETRIEVAL_RELATION: (
        "CUSTOMER_RETRIEVAL_RELATION: a project-defined retrieval hint "
        "describing how the candidate was found. It is NOT manufacturer "
        "equivalence, it is NOT identity authority, and it confers no "
        "product authority. Use it as a retrieval hint only."
    ),
}


def _present(value: str | None, absent_label: str) -> str:
    return value if value else absent_label


def _render_provenance_lines(
    case: SemanticMatchCaseV2,
) -> list[str]:
    if not case.context_provenances:
        return ["- (none)"]
    return [
        f"- {_PROVENANCE_LABELS[provenance]}"
        for provenance in sorted(
            case.context_provenances, key=lambda p: p.value
        )
    ]


def _render_product_evidence_lines(case: SemanticMatchCaseV2) -> list[str]:
    profile = case.product_evidence
    lines = [
        f"- Usable product title: {'yes' if profile.has_usable_product_title else 'no'}",
    ]
    if not profile.matched_facts:
        lines.append("- Grounded matched-attribute facts: (none)")
    else:
        lines.append("- Grounded matched-attribute facts:")
        for fact in sorted(
            profile.matched_facts,
            key=lambda f: (f.dimension.value, sorted(s.value for s in f.sources)),
        ):
            sources = ", ".join(sorted(s.value for s in fact.sources))
            lines.append(
                f"  - {fact.dimension.value} (grounded in {sources})"
            )
    return lines


def render_v2_user_prompt(case: SemanticMatchCaseV2) -> str:
    """Render the exact V2 user prompt for one recorded V2 input.

    Pure string composition over the case's five sections (A. TARGET,
    B. CANDIDATE LISTING, C. DETERMINISTIC IDENTITY CONTEXT, D. CONTEXT
    PROVENANCE, E. PRODUCT EVIDENCE). The same recorded input always
    renders the same prompt (deterministic reconstruction without any
    live call).
    """
    if not isinstance(case, SemanticMatchCaseV2):
        raise TypeError(
            "case must be SemanticMatchCaseV2, "
            f"got {type(case).__name__}"
        )
    lines: list[str] = []
    lines.append(f"COMMERCIAL SEMANTIC EQUIVALENCE CASE {case.case_id}")
    lines.append("")
    lines.append("TARGET PRODUCT:")
    lines.append(f"- Requested manufacturer part number (MPN): {case.target_mpn}")
    lines.append(
        "- Requested description: "
        + _present(case.target_description, "(not provided)")
    )
    lines.append("")
    lines.append("CANDIDATE LISTING:")
    lines.append(f"- Source URL: {case.candidate_source_url}")
    lines.append("- Title: " + _present(case.candidate_title, "(not provided)"))
    lines.append(
        "- Published MPN field: "
        + _present(case.candidate_mpn_field, "(not published)")
    )
    lines.append(
        "- Published SKU: " + _present(case.candidate_sku, "(not published)")
    )
    lines.append(
        "- Brand (separately observed): "
        + _present(case.candidate_brand, "(not observed)")
    )
    lines.append(
        "- Condition (separately observed): "
        + _present(case.candidate_condition, "(not observed)")
    )
    lines.append(
        "- Structured listing evidence: "
        + _present(
            case.candidate_specs, "(none beyond the fields above)"
        )
    )
    lines.append(
        "- Commercial context (price/package observations ONLY; NEVER "
        "identity evidence): "
        + _present(case.candidate_commercial_context, "(not observed)")
    )
    lines.append(f"- Candidate evidence source: {case.candidate_evidence_source}")
    lines.append("")
    lines.append(
        "DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; "
        "you cannot override it):"
    )
    lines.append(f"- Identity state: {case.identity_state.value}")
    lines.append(f"- Substate: {case.substate.value}")
    lines.append(
        "- Primary identifier relationship signal: "
        + case.primary_relationship_signal.value
    )
    lines.append(
        "- All bounded relationship signals: "
        + (
            ", ".join(
                sorted(s.value for s in case.relationship_signals)
            )
            if case.relationship_signals
            else "(none)"
        )
    )
    lines.append(
        "- Normalized requested MPN: "
        + _present(case.normalized_requested_part_number, "(none)")
    )
    lines.append(
        "- Normalized candidate MPN: "
        + _present(case.normalized_candidate_part_number, "(none)")
    )
    lines.append(
        "- Relationship requirement: "
        + case.relationship_requirement.value
    )
    lines.append("")
    lines.append("CONTEXT PROVENANCE:")
    lines.extend(_render_provenance_lines(case))
    lines.append("")
    lines.append(
        "PRODUCT EVIDENCE (authority-side evidence from deterministic/"
        "reviewed sources only; you may observe it but must NOT create, "
        "upgrade, or assert new product evidence):"
    )
    lines.extend(_render_product_evidence_lines(case))
    return "\n".join(lines)


@dataclass(frozen=True)
class SemanticPromptV2:
    """A constructed final Semantic V2 prompt with version tracking.

    ``case`` is the exact recorded V2 input the prompt renders: together
    with ``SEMANTIC_PROMPT_VERSION_V2`` it makes the historical prompt
    deterministically reconstructable without any live call.
    """

    version: str
    system_prompt: str
    user_prompt: str
    case: SemanticMatchCaseV2

    def __post_init__(self) -> None:
        if self.version != SEMANTIC_PROMPT_VERSION_V2:
            raise ValueError(
                f"version must be {SEMANTIC_PROMPT_VERSION_V2!r}, "
                f"got {self.version!r}"
            )
        if not isinstance(self.system_prompt, str) or not self.system_prompt:
            raise TypeError("system_prompt must be a non-empty str")
        if not isinstance(self.user_prompt, str) or not self.user_prompt:
            raise TypeError("user_prompt must be a non-empty str")
        if not isinstance(self.case, SemanticMatchCaseV2):
            raise TypeError(
                "case must be SemanticMatchCaseV2, "
                f"got {type(self.case).__name__}"
            )


def build_semantic_prompt_v2(case: SemanticMatchCaseV2) -> SemanticPromptV2:
    """Build the FINAL Prompt V2 for one V2 input case.

    The system prompt is the frozen ``SYSTEM_PROMPT_V2``; the user prompt
    is the deterministic rendering of the case's five sections. No other
    input exists: a prompt for a different case or a different version
    cannot be produced through this builder.
    """
    return SemanticPromptV2(
        version=SEMANTIC_PROMPT_VERSION_V2,
        system_prompt=SYSTEM_PROMPT_V2,
        user_prompt=render_v2_user_prompt(case),
        case=case,
    )
