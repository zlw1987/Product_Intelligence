"""The FINAL Prompt V2 (S2-C, corrected in place by S2-C-FU1 before freeze).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-S2-C freezes the exact prompt that
Qualification V3 will use UNCHANGED unless an actual defect is discovered
before qualification. S2-C is REVIEWED but NOT APPROVED / NOT FROZEN and
MUST NOT deploy, and no historical production V2 record exists anywhere
(the semantic-decision ledger table is absent from the development
database; V2 is persist-only and unqualified). FU1 therefore amends the
PRE-FREEZE candidate prompt in place: the prompt version stays ``2.0``
because 2.0 never shipped — the frozen 2.0 that Qualification V3
qualifies against is the corrected text.

* ``SEMANTIC_PROMPT_VERSION_V2 = "2.0"`` — the prompt version of the
  Semantic V2 contract (independent of the persistence envelope version,
  the semantic contract version, and the runtime route version);
* ``SYSTEM_PROMPT_V2`` — the frozen system prompt: the task is COMMERCIAL
  SEMANTIC EQUIVALENCE of the TARGET product and the CANDIDATE listing,
  with the explicit rules it is NOT asked to do (no price estimation, no
  machine-verified decisions, no overriding deterministic HARD_CONFLICT,
  no inferring manufacturer authority, no turning customer aliases into
  manufacturer equivalence, no market-aggregation decisions), the
  EVIDENCE CLASS rules (STRUCTURED FACT vs RAW OBSERVATION TEXT vs
  COMMERCIAL / PACKAGING EVIDENCE vs REVIEWED TARGET CONTEXT vs
  AUTHORITY-SIDE PRODUCT EVIDENCE; absence of packaging evidence is not
  proof of equal sales unit; raw text never becomes manufacturer
  authority; never manufacture a missing fact), and the explicit
  behavioral rules (exact MPN equality is strong but not the only
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

from product_intelligence.research import (
    CandidateEvidenceSourceV2,
    ContextProvenance,
    PackagingEvidenceStateV2,
    TargetIdentifierRelationKindV2,
)
from product_intelligence.research.semantic_v2 import (
    CandidateObservationFactV2,
    CandidateSalesUnitEvidenceV2,
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
mirrored constant.

S2-C-FU1 versioning decision: S2-C is REVIEWED but NOT APPROVED / NOT
FROZEN and MUST NOT deploy, and no historical production V2 record exists
anywhere. FU1 amends the PRE-FREEZE candidate prompt in place; the
version stays 2.0 because 2.0 never shipped. Bumping to a phantom 2.1
would falsely claim a frozen 2.0 with live records."""


SYSTEM_PROMPT_V2: Final[str] = """You are a product commercial-equivalence evaluation assistant.

TASK
Your task is to determine the COMMERCIAL SEMANTIC EQUIVALENCE of a TARGET product and a CANDIDATE listing: does the candidate listing represent the same commercially comparable product as the target, and with what confidence?

You are given a structured input with five sections: TARGET, CANDIDATE LISTING, DETERMINISTIC IDENTITY CONTEXT, CONTEXT PROVENANCE, and PRODUCT EVIDENCE. Use ONLY the evidence supplied in those sections. Do not rely on unstated specifications, catalog knowledge, or outside product knowledge. Every value in the input is labeled with its evidence class (STRUCTURED FACT with a source label, RAW OBSERVATION TEXT, COMMERCIAL / PACKAGING EVIDENCE, REVIEWED TARGET CONTEXT, or AUTHORITY-SIDE PRODUCT EVIDENCE); read every value in its class.

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

EVIDENCE CLASSES (how to read the input)
- STRUCTURED FACT: a bounded value with an explicit source label (published structured field, listing title, specification text, or reviewed manufacturer product context). A structured fact is an OBSERVATION about one side of the comparison: it may support your reasoning, but it is not by itself a proof that the two sides agree. Equivalence between the sides is your semantic judgment.
- RAW OBSERVATION TEXT: free text as published (the listing title, the requested description). Raw text may support semantic reasoning, but a token occurring in raw text is NOT a structured fact, and raw text NEVER becomes manufacturer authority. Absence of a structured fact does not erase the raw observation evidence; the absence of both is not a value.
- COMMERCIAL / PACKAGING EVIDENCE: price, currency, availability, seller, condition, offer, and the sales-unit / packaging channel. Commercial evidence is NEVER identity evidence. The sales-unit channel is EXPLICIT: "UNAVAILABLE" means the listing published no packaging / sales-unit field. Absence of packaging evidence is NOT proof of equal sales unit and is never read as "single unit"; do not infer a packaging value from price or from any other commercial fact.
- REVIEWED TARGET CONTEXT: when present, a structured/reviewed manufacturer context about the TARGET (never about the candidate). It may strengthen your understanding of the requested product. Its identifier relation, when present, is customer-retrieval-only: zero identity authority, never manufacturer equivalence.
- AUTHORITY-SIDE PRODUCT EVIDENCE: the PRODUCT EVIDENCE section (deterministic/reviewed only). You may observe it; you must NOT create, upgrade, or assert new product evidence: your matched_attributes are conclusions about equivalence, not new authority-side facts.
- NEVER MANUFACTURE A MISSING FACT: if a critical attribute is absent from ALL supplied evidence, name it in missing_critical_attributes. Do not fill a gap with a guess or with outside knowledge.

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
- When the candidate's sales-unit / packaging channel is UNAVAILABLE, sales-unit equivalence is UNPROVEN: if the comparison otherwise supports MATCH and the sales unit is critical to commercial comparability, report PACKAGING_QUANTITY (and/or BUNDLE) in missing_critical_attributes and return UNCERTAIN with UNCERTAIN_MISSING_CRITICAL_ATTRIBUTES rather than guessing packaging equivalence.

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


# Frozen rendering labels for the bounded evidence sources of a structured
# fact. The wording is contract: a structured fact always renders with its
# provenance label, and RAW observation text always renders under its raw-
# text label (S2-C-FU1: the model must be able to tell structured from raw).
_SOURCE_LABELS: Final[dict[CandidateEvidenceSourceV2, str]] = {
    CandidateEvidenceSourceV2.PUBLISHED_STRUCTURED_FIELD: (
        "published structured field"
    ),
    CandidateEvidenceSourceV2.LISTING_TITLE: "listing title",
    CandidateEvidenceSourceV2.SPECIFICATION_TEXT: "specification text",
    CandidateEvidenceSourceV2.REVIEWED_PRODUCT_CONTEXT: (
        "reviewed manufacturer product context"
    ),
}

#: Frozen rendering labels for the bounded reviewed-target identifier-
#: relation kinds. The wording is contract: the customer-retrieval kind is
#: rendered as retrieval-only, NEVER as manufacturer equivalence.
_RELATION_KIND_LABELS: Final[dict[TargetIdentifierRelationKindV2, str]] = {
    TargetIdentifierRelationKindV2.CUSTOMER_RETRIEVAL_ALIAS: (
        "customer-defined retrieval relation; NOT manufacturer-stated; zero "
        "identity authority"
    ),
}


def _present(value: str | None, absent_label: str) -> str:
    return value if value else absent_label


def _render_fact(fact: CandidateObservationFactV2 | None) -> str:
    """One bounded observation fact with its source label, or the explicit
    absence (never a guess)."""
    if fact is None:
        return "(none)"
    return f'"{fact.value}" [{_SOURCE_LABELS[fact.source]}]'


def _render_sales_unit(su: CandidateSalesUnitEvidenceV2) -> str:
    """The explicit sales-unit / packaging channel rendering.

    UNAVAILABLE renders as an explicit recorded absence with the
    never-infer rule; OBSERVED renders the bounded kind, quantity (when
    present), the published raw detail, and the source label."""
    if not isinstance(su, CandidateSalesUnitEvidenceV2):
        raise TypeError(
            "sales unit evidence must be CandidateSalesUnitEvidenceV2, got "
            f"{type(su).__name__}"
        )
    if su.state is PackagingEvidenceStateV2.UNAVAILABLE:
        return (
            "UNAVAILABLE — the listing published no packaging / sales-unit "
            "field; absence is NOT proof of equal sales unit (do not infer "
            "a single unit)"
        )
    parts = [f"OBSERVED — kind: {su.kind.value}"]
    if su.quantity is not None:
        parts.append(f"quantity: {su.quantity}")
    parts.append(f'as published: "{su.raw_detail}" [{_SOURCE_LABELS[su.source]}]')
    return "; ".join(parts)


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
    lines.append(
        "- Requested MPN (STRUCTURED; caller-published; the run's identity "
        f"anchor): {case.target.mpn}"
    )
    lines.append(
        "- Requested description (RAW OBSERVATION TEXT; may support "
        "reasoning; not a reviewed specification): "
        + _present(case.target.description_raw_text, "(not provided)")
    )
    reviewed = case.target.reviewed_context
    if reviewed is None:
        lines.append(
            "- Reviewed manufacturer target context: "
            "(none carried by the execution flow)"
        )
    else:
        lines.append(
            "- Reviewed manufacturer target context (STRUCTURED/REVIEWED; "
            "target-side only; zero identity authority):"
        )
        lines.append(f"  - Manufacturer: {reviewed.manufacturer}")
        lines.append(f"  - Verified category: {reviewed.category}")
        lines.append(
            "  - Matched base part number (source-published): "
            + reviewed.matched_base_part_number
        )
        lines.append(
            f"  - Identifier relation to requested MPN: "
            f"{reviewed.relation_kind.value} — "
            f"{_RELATION_KIND_LABELS[reviewed.relation_kind]}; "
            f"family part numbers other than the requested form: "
            f"{', '.join(reviewed.relation_family_part_numbers)}"
        )
        lines.append(f"  - Source: {reviewed.source_name}")
        lines.append(f"  - Source URL: {reviewed.source_url}")
        lines.append(f"  - Retrieved at: {reviewed.retrieved_at}")
        lines.append(f"  - Evidence body SHA-256: {reviewed.evidence_body_sha256}")
    lines.append("")
    lines.append("CANDIDATE LISTING:")
    lines.append(f"- Source URL: {case.candidate_source_url}")
    lines.append(
        "- Published MPN field: "
        + _present(case.candidate_mpn_field, "(not published)")
    )
    lines.append(
        "- Published SKU: " + _present(case.candidate_sku, "(not published)")
    )
    lines.append(f"- Candidate evidence source: {case.candidate_evidence_source}")
    lines.append("")
    lines.append(
        "Structured product evidence (bounded facts with source labels; "
        "absent = not observed, never a guess):"
    )
    product = case.candidate_product
    lines.append(f"- product_family: {_render_fact(product.product_family)}")
    lines.append(f"- generation: {_render_fact(product.generation)}")
    lines.append(f"- capacity: {_render_fact(product.capacity)}")
    lines.append(f"- interface: {_render_fact(product.interface)}")
    lines.append(f"- form_factor: {_render_fact(product.form_factor)}")
    lines.append(f"- product_role: {_render_fact(product.product_role)}")
    lines.append(
        f"- accessory_relation: {_render_fact(product.accessory_relation)}"
    )
    lines.append(f"- brand: {_render_fact(product.brand)}")
    lines.append(
        f"- revision_or_suffix: {_render_fact(product.revision_or_suffix)}"
    )
    lines.append("")
    lines.append(
        "Raw observation text (may support semantic reasoning; NOT "
        "structured evidence; never manufacturer authority):"
    )
    lines.append(
        "- Listing title: "
        + (
            f'"{product.raw_title_text}"'
            if product.raw_title_text
            else "(not provided)"
        )
    )
    lines.append(
        "- Specification text: "
        + (
            f'"{product.raw_specification_text}"'
            if product.raw_specification_text
            else "(none carried by the extractor)"
        )
    )
    lines.append("")
    commercial = case.candidate_commercial
    lines.append("Commercial / packaging evidence (NEVER identity evidence):")
    lines.append(f"- condition: {_render_fact(commercial.condition)}")
    lines.append(f"- price: {_render_fact(commercial.price)}")
    lines.append(f"- currency: {_render_fact(commercial.currency)}")
    lines.append(f"- availability: {_render_fact(commercial.availability)}")
    lines.append(f"- seller: {_render_fact(commercial.seller)}")
    lines.append(
        "- Offer URL: " + _present(commercial.offer_url, "(not published)")
    )
    lines.append(f"- Sales unit / packaging: {_render_sales_unit(commercial.sales_unit)}")
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
