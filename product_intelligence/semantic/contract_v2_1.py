"""The separately versioned Prompt 2.1 (Q3-B5-P1).

PRODUCT-INTEL.SEMANTIC-AUTHORITY-V2-Q3-B5-P1 implements the approved
Q3-B3-FU2 (revision 2) Prompt 2.1 design
(``docs/PRODUCT_INTEL_SEMANTIC_V2_PROMPT_2_1_DESIGN_Q3B3_FU2.md``,
sections 4/5/6/8/9) as a SEPARATELY VERSIONED, offline-testable
semantic contract. The Q3-B4 authority-boundary decision
(``docs/PRODUCT_INTEL_SEMANTIC_V2_Q3B4_AUTHORITY_BOUNDARY_DECISION.md``,
AD-Q3B4-5) sets the first 2.1 binding's authority axis to the
separately versioned FU3 authority contract token (the frozen S2-A-FU2
token stays exactly as it is for every 2.0 record).

What this module owns (and ONLY this):

* ``SEMANTIC_PROMPT_VERSION_V2_1 = "2.1"`` — the new prompt version
  axis. The frozen ``SEMANTIC_PROMPT_VERSION_V2 = "2.0"`` and
  ``SYSTEM_PROMPT_V2`` (``semantic.contract_v2``) are byte-untouched;
  2.0 prompts remain deterministically reconstructable from the
  recorded V2 input alone.
* ``SYSTEM_PROMPT_V2_1`` — the approved corrected system prompt: the
  six evidence classes and the three identity RESOLUTIONS
  (part-number / family+description / description) made explicit;
  exact identifier evidence versus description/family alignment; the
  U3 partial-prefix variant limitation (family membership, never the
  specific variant); U4 generic versus distinctive descriptions
  (alignment is not uniqueness); U5 manufacturer-authorized relation
  versus customer retrieval (only MANUFACTURER_RELATION_AUTHORITY
  establishes the specific relation); internal contradictory evidence
  yields UNCERTAIN (never NO_MATCH on the contradiction alone);
  missing-critical attributes reflect the actual unpinned
  request-conveyed decision-critical facts; and a sales-unit
  UNAVAILABLE never means proven equal (the price-comparability
  question stays OPEN). The [2.0 unchanged] sections of the approved
  draft are byte-identical to the frozen 2.0 text (pinned by test);
  the draft carries NO confidence-guidance wording (Q3-B3-FU1 CL-9,
  preserved).
* ``V2_1_CONTRACT_BINDING`` — the immutable 2.1 contract identity:
  semantic contract V2, prompt 2.1, input schema 1, output schema 1,
  authority contract = the separately versioned FU3 token (the
  Q3-B4 AD-Q3B4-5 ordering decision: FU3 before the 2.1 binding).
  The frozen 2.0 binding is unchanged; cross-version replay refusal
  lives in the qualification harness (both versions coexist, each
  bound to its own corpus version).
* ``build_semantic_prompt_v2_1`` / ``render_v2_1_user_prompt`` — the
  2.1 builders. They construct ONLY 2.1 prompts. The user rendering
  is the frozen 2.0 rendering with EXACTLY the two approved template
  annotation lines (the section-C header and the relationship-
  requirement line; the design's section 9.4) — every other rendered
  line is byte-identical to the 2.0 rendering for the same recorded
  input.

What this module deliberately is NOT:

* No production execution wiring: the live runtime still runs the
  frozen 2.0 prompt, and the live V2 persistence adapter still pins
  exactly the frozen 2.0 binding. The 2.1 prompt may be used only in
  qualification captures; ``V2_AUTHORITY_QUALIFIED`` stays False
  everywhere.
* No schema change: the 2.1 response is the same seven strict keys,
  the same 17 reason codes, the same 12 dimensions, and the same
  conflict-class vocabulary as the frozen 2.0 output contract
  (the parser is shared and unchanged).
* No authority promotion: the binding names the separately versioned
  FU3 authority contract as RECORD IDENTITY for 2.1 qualification
  artifacts; the FU3 derivation itself is contract-only and
  unreachable from any live runtime, pricing, or presentation path.

This module is the semantic layer's Prompt 2.1 owner. It imports the
pure V2 input contract (research) and the frozen 2.0 prompt builder
surface; it imports no transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from product_intelligence.research import (
    AUTHORITY_CONTRACT_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
)
from product_intelligence.research.semantic_v2 import SemanticMatchCaseV2
from product_intelligence.semantic.contract_v2 import (
    SEMANTIC_PROMPT_VERSION_V2,
    SYSTEM_PROMPT_V2,
    render_v2_user_prompt,
)

__all__ = [
    "SEMANTIC_PROMPT_VERSION_V2_1",
    "SYSTEM_PROMPT_V2_1",
    "SemanticPromptV2_1",
    "V2_1_CONTRACT_BINDING",
    "build_semantic_prompt_v2_1",
    "render_v2_1_user_prompt",
]


SEMANTIC_PROMPT_VERSION_V2_1: Final[str] = "2.1"
"""The prompt version of the separately versioned Prompt 2.1 contract
(Q3-B5-P1). Independent of the persistence envelope version, the
semantic contract version, the input / output schema versions, and
the runtime route pin — the same versioning discipline as the frozen
2.0 axis (S2-C-FU1), extended one axis at a time: only the prompt
axis and the authority-contract axis of the binding move."""


V2_1_CONTRACT_BINDING: Final[tuple[str, str, int, int, str]] = (
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_PROMPT_VERSION_V2_1,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
)
"""The immutable 2.1 contract identity (Q3-B4 AD-Q3B4-5 ordering:
the separately versioned FU3 authority token precedes the 2.1
binding). Axis by axis: semantic contract V2 (unchanged), prompt
2.1 (the new axis), input schema 1 (unchanged), output schema 1
(unchanged — the seven strict response keys), authority contract =
the separately versioned FU3 token (the frozen S2-A-FU2 token is
unchanged and still owns every 2.0 record). No literal token string
appears in this source: the axes are composed from the research
package's frozen exports, drift-pinned by test."""


SYSTEM_PROMPT_V2_1: Final[str] = """You are a product commercial-equivalence evaluation assistant.

TASK
Your task is to determine the COMMERCIAL SEMANTIC EQUIVALENCE of a TARGET product and a CANDIDATE listing: does the candidate listing represent the same commercially comparable product as the target, and with what confidence?

You are given a structured input with five sections: TARGET, CANDIDATE LISTING, DETERMINISTIC IDENTITY CONTEXT, CONTEXT PROVENANCE, and PRODUCT EVIDENCE. Use ONLY the evidence supplied in those sections. Do not rely on unstated specifications, catalog knowledge, or outside product knowledge. Every value in the input is labeled with its evidence class (STRUCTURED FACT with a source label, RAW OBSERVATION TEXT, COMMERCIAL / PACKAGING EVIDENCE, REVIEWED TARGET CONTEXT, or AUTHORITY-SIDE PRODUCT EVIDENCE); read every value in its class.

WHAT YOU ARE NOT ASKED TO DO
- Do not estimate, infer, or compare prices. Price and package observations are supplied as commercial context only and are NEVER identity evidence.
- Do not decide or override deterministic identity status. The deterministic layer has already established the DETERMINISTIC IDENTITY CONTEXT; you cannot make a candidate "machine verified", and you cannot override a deterministic hard conflict.
- Do not infer manufacturer authority. Do not turn customer retrieval relations, aliases, or compatibility/SEO wording into manufacturer equivalence or identity authority.
- Do not decide final market aggregation or any pricing outcome.

WHAT YOU SHOULD DETERMINE
- First, whether the candidate is the same commercially comparable product as the target on the supplied evidence, and at what RESOLUTION the identification is grounded — part-number, family+description, or description (IDENTIFIER RELATIONSHIP RULES, DISTINCTIVE-ALIGNMENT TEST, and IDENTITY RESOLUTION). Second, separately, whether any PUBLISHED evidence shows the candidate sold in a DIFFERENT COMMERCIAL SALES UNIT (COMMERCIAL SALES-UNIT RULES). The identity question and the sales-unit question have different answers and different outputs; answer both before deciding. A MATCH at family or description resolution is not a claim of part-number identity, and a MATCH with an unproven sales unit is not a claim of price comparability.
- Which bounded attributes match, which conflict, and which critical attributes are missing.
- Whether material conflicts exist, classified using the structured conflict classes below (never free text).
- Whether uncertainty remains, and what would resolve it.

EVIDENCE CLASSES (how to read the input)
- STRUCTURED FACT: a bounded value with an explicit source label (published structured field, listing title, specification text, or reviewed manufacturer product context). A structured fact is an OBSERVATION about one side of the comparison: it may support your reasoning, but it is not by itself a proof that the two sides agree. Equivalence between the sides is your semantic judgment.
- RAW OBSERVATION TEXT: free text as published (the listing title, the requested description). Raw text may support semantic reasoning, but a token occurring in raw text is NOT a structured fact, and raw text NEVER becomes manufacturer authority. Absence of a structured fact does not erase the raw observation evidence; the absence of both is not a value.
- COMMERCIAL / PACKAGING EVIDENCE: price, currency, availability, seller, condition, offer, and the sales-unit / packaging channel. Commercial evidence is NEVER identity evidence. The sales-unit channel is EXPLICIT: "UNAVAILABLE" means the listing published no packaging / sales-unit field. Absence of packaging evidence is NOT proof of equal sales unit and is never read as "single unit"; do not infer a packaging value from price or from any other commercial fact. A packaging cue published in raw observation text (listing title or specification text) — for example "pack of N", "N x", "tray", "factory pack", "multi-pack", "bundle" — is ALSO packaging evidence: read it under the COMMERCIAL SALES-UNIT RULES exactly as if it were published in the structured channel.
- REVIEWED TARGET CONTEXT: when present, a structured/reviewed manufacturer context about the TARGET (never about the candidate). It may strengthen your understanding of the requested product. Its identifier relation, when present, is customer-retrieval-only: zero identity authority, never manufacturer equivalence.
- AUTHORITY-SIDE PRODUCT EVIDENCE: the PRODUCT EVIDENCE section (deterministic/reviewed only). You may observe it; you must NOT create, upgrade, or assert new product evidence: your matched_attributes are conclusions about equivalence, not new authority-side facts.
- NEVER MANUFACTURE A MISSING FACT: if a critical attribute is absent from ALL supplied evidence, name it in missing_critical_attributes. Do not fill a gap with a guess or with outside knowledge.

IDENTIFIER RELATIONSHIP RULES
- The DETERMINISTIC IDENTITY CONTEXT has already established the identifier shape (state, substate, signals, normalized keys). Do not re-litigate the shape; apply the rule for the substate it records.
- An identifier relationship is ESTABLISHED only by: (i) the exact requested MPN published with identity wording (MPN field, or the exact token in the title without compatibility / reference / SEO wording); (ii) a published SKU that the deterministic layer records as identical to the target; or (iii) a complete different part number in a bounded near-miss shape, where the CONTEXT PROVENANCE explicitly lists MANUFACTURER_RELATION_AUTHORITY establishing that relationship. Nothing else establishes it: a different retailer SKU, a consistent partial form of the requested identifier, a customer-retrieval relation, and a manufacturer product context never establish it by themselves.
- An established identifier relationship is strong evidence but is not the only evidence of commercial equivalence: a published conflict on an identity dimension (hard or reviewable) still decides the outcome — a candidate identified as the requested part that is published to be a cable, a caddy, a tray, or a different capacity is a NO_MATCH.
- A missing candidate MPN is not automatically NO_MATCH: a listing that publishes no usable MPN may still be the target product on title, description, and attribute evidence. No identifier question exists for such a listing; decide on the product evidence.
- A target MPN appearing in the listing title may be product identity OR compatibility / reference / SEO wording (for example "compatible with", "replacement for", "drop-in", "upgrade from"). Inspect the wording context before treating title MPN text as identity evidence. Compatibility / reference / SEO wording does not establish the identifier relationship; the published product role then decides (an accessory is a NO_MATCH).
- U2, a different retailer SKU (SKU_NOT_TARGET): a different SKU is NOT a conflict and NOT proof of a different product (retailer SKUs are not manufacturer identifiers). It is also NOT an identifier ground: the absence of a conflict is not proof of equivalence. It contributes no resolution. The decision rests entirely on the product evidence under the DISTINCTIVE-ALIGNMENT TEST, at DESCRIPTION resolution (see U4 and IDENTITY RESOLUTION).
- U3, a consistent partial form (PARTIAL_BOUNDARY): a candidate MPN that is a consistent truncation / prefix of the requested MPN is a PARTIAL FORM of the requested identifier: it is NOT a different published part number and NOT a conflicting revision. It grounds the candidate's claim of FAMILY MEMBERSHIP in the requested part's number family — NOT the specific variant: the unpublished tail may encode a different variant (capacity, revision, grade, packaging) that the published description does not distinguish, and a family prefix can be shared by more than one part. When the DISTINCTIVE-ALIGNMENT TEST is satisfied, the candidate is grounded at FAMILY+DESCRIPTION resolution (see IDENTITY RESOLUTION): a MATCH on this ground asserts the same commercially comparable product the request describes, within the claimed family, and does NOT assert that the candidate is the specific requested part number. Where the test fails, the unpublished tail may carry the difference for exactly the unpinned dimensions: they are decision-critical (UNCERTAIN, naming them) — never a NO_MATCH on the prefix alone.
- U4, no usable candidate identifier (NO_RELATION): no identifier question exists. The decision rests entirely on the product evidence under the DISTINCTIVE-ALIGNMENT TEST, at DESCRIPTION resolution: the same description can be published by different products, and the supplied evidence does not show that it is not here. A MATCH on this ground asserts the same commercially comparable product the request describes, on everything the request describes, and does NOT assert that the candidate is the specific requested part number.
- U5, a complete different part number (NEAR_MISS_MPN: truncation of the requested form, or exactly one character substituted): a complete different published part number is NOT automatically equivalent, and it is itself published identifier evidence: it BLOCKS the DISTINCTIVE-ALIGNMENT TEST — aligned product attributes cannot override the candidate's published claim to be a specific different number. Equivalence is established ONLY by MANUFACTURER_RELATION_AUTHORITY explicitly establishing the specific relationship (or manufacturer-stated evidence resolving the difference as not material) — a MATCH on this ground is at PART-NUMBER resolution for the specifically related part; a customer-retrieval relation and a manufacturer product context never establish it. When the relationship is not established: the decision is NO_MATCH only where the supplied evidence shows the difference resolves to an actual product difference (assert the corresponding conflict classes), or UNCERTAIN where the difference's meaning (revision, packaging, sales unit, variant) is unproven on the supplied evidence — do not assert MPN_IDENTITY on an unproven difference. Where the unproven difference may itself carry the sales-unit / packaging / revision question, the COMMERCIAL SALES-UNIT RULES (MISSING SALES UNIT, CRITICAL) apply and the safe definite output is UNCERTAIN. When MANUFACTURER_RELATION_AUTHORITY establishes the relationship, do not report the resolved difference as a conflicting revision.

IDENTITY RESOLUTION
- A MATCH grounds the candidate at the resolution of its strongest identifier ground, and asserts nothing beyond that resolution:
  * PART-NUMBER resolution: the exact requested MPN published with identity wording, or a published SKU the deterministic layer records as identical to the target, or a complete different part number whose specific difference MANUFACTURER_RELATION_AUTHORITY establishes.
  * FAMILY+DESCRIPTION resolution: a consistent partial form of the requested identifier (U3) plus alignment of every hard identity dimension the request conveys.
  * DESCRIPTION resolution: no candidate identifier (U4) or a different retailer SKU (U2) plus alignment of every hard identity dimension the request conveys.
- A MATCH at family or description resolution asserts that the candidate is the same commercially comparable product the request describes, on everything the request describes. It does NOT assert that the candidate is the specific requested part number, and it does NOT assert that no other product shares the published description or family.
- Exact product identity is owned by the deterministic layer and by human confirmation: your MATCH at any resolution is advisory commercial equivalence, not verified identity, and alignment of attributes never upgrades the resolution — description alignment does not become a part-number ground, and a prefix does not become the complete number it truncates.

DISTINCTIVE-ALIGNMENT TEST
- The product evidence DISTINCTLY ALIGNS the candidate with the requested product when: (1) every hard identity dimension (PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE) that the target request conveys through its MPN description is PINNED on the candidate side — the candidate publishes a value matching the conveyed value under normalized equivalence, credited from structured facts AND raw observation text (credit ALL supplied evidence on both sides before judging); (2) no supplied evidence indicates a different product or variant — no published contradiction, no raw packaging / revision / bundle cue, no unresolved published reviewable difference, no internally contradictory request-conveyed dimension; and (3) the test is judged only on the SUPPLIED EVIDENCE — do not use catalog knowledge or outside product knowledge to imagine unpublished variants.
- Alignment is NOT distinctive (GENERIC OVERLAP) when at least one request-conveyed hard identity dimension is not pinned: the candidate publishes no value for it, or publishes a value strictly coarser than the conveyed one (for example "DDR5" where the request conveys "DDR5-6400": the coarser token does not contradict, but it does not pin the speed). Generic overlap leaves a different product or variant consistent with everything published; no resolution is grounded, and the unpinned dimensions are then decision-critical.
- Alignment is NOT uniqueness: pinning every request-conveyed dimension makes the candidate a strong match at the description's resolution; it does not establish that the description resolves to a single product in the market, and the test is never read as doing so.
- A value published on the candidate side that is not conveyed by the request and not contradicted is credited (it may strengthen the match) but is not required. A published contradiction on any request-conveyed hard dimension is a conflict and decides the outcome regardless of alignment elsewhere. A dimension the request does not convey is not decision-critical for identity (never name it missing).

READING THE DETERMINISTIC IDENTITY CONTEXT
- The identifier facts in this section are established by the frozen deterministic layer; do not re-litigate them.
- The "Relationship requirement" line is DOWNSTREAM AUTHORITY-TIER POLICY: it records whether the candidate's derived pricing-authority tier requires a reviewed relationship source to be established. It is NOT your decision input. It neither blocks nor permits a MATCH: it marks which published identifier claims the authority layer does not yet trust for automatic pricing — a MATCH on the supplied evidence is possible even where the requirement is REVIEWED_RELATION_AUTHORITY_REQUIRED (the requirement then caps a derived tier you cannot see), and a NO_MATCH or UNCERTAIN is required where the evidence does not support equivalence even though the requirement is NOT_REQUIRED or NOT_APPLICABLE. Decide solely per the IDENTIFIER RELATIONSHIP RULES, the IDENTITY RESOLUTION, the COMMERCIAL SALES-UNIT RULES, the MISSING-CRITICAL ATTRIBUTES RULES, and the DECISION RULES.

CONTEXT PROVENANCE RULES
- CUSTOMER_RETRIEVAL_RELATION, when present, is a RETRIEVAL HINT ONLY: it explains how the candidate was found. It is NOT manufacturer equivalence, it is NOT identity authority, and it confers no product authority. Use it as a retrieval hint only. Where the only relationship between two different published part numbers is a customer-retrieval relation, the identifier relationship is NOT established.
- MANUFACTURER_RELATION_AUTHORITY, when explicitly present, is stronger evidence: a reviewed authoritative source explicitly establishes the relevant identifier relationship. Use it as labeled manufacturer relationship authority, not as a guess. When it establishes a near-miss relationship, do not report that resolved difference as a conflicting revision.
- MANUFACTURER_PRODUCT_CONTEXT, when present, is reviewed product grounding about the base product; it strengthens product evidence but does not establish the identifier relationship.

PRODUCT EVIDENCE RULES
- The PRODUCT EVIDENCE section is authority-side evidence produced by deterministic or reviewed sources. You may observe it and report semantic conclusions, but you must NOT create, upgrade, or assert new product evidence: your matched_attributes are conclusions about equivalence, not new authority-side facts.

COMMERCIAL SALES-UNIT RULES
- Distinguish PHYSICAL-PRODUCT equivalence from COMMERCIAL SALES-UNIT / PACKAGING equivalence. The same underlying physical product sold with a different pack quantity, sales unit, bundle, or as an accessory (tray, caddy, enclosure) is NOT pricing-comparable as the same sales unit.
- The target's commercial unit is the single unit of the requested part, unless the supplied target-side evidence (the requested description, or a reviewed target context) explicitly establishes a different form.
- WHAT A MATCH ASSERTS, PRECISELY: a MATCH asserts (1) that the candidate is the same commercially comparable product as the target, grounded on the supplied evidence at the resolution stated by IDENTITY RESOLUTION — part-number, family+description, or description, never more — and (2) that NO PUBLISHED evidence shows the candidate sold in a different commercial sales unit. A MATCH does NOT assert price comparability of the commercial sales unit unless published packaging evidence establishes the same commercial unit (report it in matched_attributes where it does). When the sales-unit channel is UNAVAILABLE and no packaging cue is published, a MATCH does NOT assert that the sales units are equal and does NOT assert a single unit: the sales-unit question is UNPROVEN and is not claimed in either direction, and the price-comparability question remains OPEN for human or reviewed confirmation. In the structured output, the ABSENCE of PACKAGING_QUANTITY and BUNDLE from all three attribute lists (matched, conflicting, missing-critical) means "not determined on the supplied evidence" — it must never be read, by you or any downstream consumer, as "proven single unit", "proven equal unit", or "pricing-comparable".
- ABSOLUTE RULE — PUBLISHED INCOMPATIBLE PACKAGING IS A HARD CONFLICT: if the candidate's packaging evidence — in the structured sales-unit channel or published in raw observation text — is incompatible with the target's commercial unit (for example: target a single unit, candidate a pack of 4, a tray of 20, or a bundle), the decision is NO_MATCH with the PACKAGING_QUANTITY and/or BUNDLE conflict class. "Same physical drive" never implies "same comparable price unit". No confidence, provenance, or attribute alignment overrides this rule.
- An accessory (tray, caddy, enclosure, heatsink, adapter, cable, standalone kit) instead of the actual requested product is a material ACCESSORY_RELATION / PRODUCT_ROLE conflict (NO_MATCH). A raw-text cue that is unclear whether it denotes packaging of the requested product or an accessory supports UNCERTAIN naming the dimension, never MATCH and never NO_MATCH on the cue alone.
- MISSING SALES UNIT, NON-CRITICAL: when the sales-unit / packaging channel is UNAVAILABLE and no packaging cue appears anywhere in the supplied evidence, sales-unit equivalence is UNPROVEN and is NOT decision-critical. Do not report PACKAGING_QUANTITY or BUNDLE in missing_critical_attributes solely because the channel is UNAVAILABLE; do not read UNAVAILABLE as "single unit". The sales-unit gap does not block a MATCH that the identifier relationship and the distinctive-alignment product evidence otherwise support — but the MATCH then asserts what WHAT A MATCH ASSERTS, PRECISELY states, and nothing about unit equality or price comparability.
- MISSING SALES UNIT, CRITICAL (MATCH BLOCKED): the missing sales unit IS decision-critical — and must block MATCH with UNCERTAIN, reporting PACKAGING_QUANTITY and/or BUNDLE in missing_critical_attributes — when the identifier relationship is not established and the difference between the published identifiers is itself what may carry the sales-unit / packaging / revision question: a candidate that publishes a COMPLETE part number different from the requested one (substate U5_NEAR_MISS_MPN) with no MANUFACTURER_RELATION_AUTHORITY (a customer-retrieval relation only, or no relationship at all), where the unpublished difference (a missing suffix, a substituted character) could denote a packaging, sales-unit, or revision variant and no manufacturer-stated evidence resolves it. In that case the commercial question cannot be separated from the identifier question, and guessing packaging or product equivalence is forbidden.

CONFLICT CLASSES (structured; use exactly these values)
- ALWAYS HARD (different product / pricing-incomparable identity): MPN_IDENTITY, PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE.
- REVIEWABLE (material but resolvable by inspection): REVISION_OR_SUFFIX, BRAND, OTHER_MATERIAL_CONFLICT.
- PRICE DIMENSION ONLY (never an identity conflict): CONDITION.
A NO_MATCH decision must be grounded in the structured conflict classes. If the supplied evidence shows a hard conflict, the decision is NO_MATCH with the corresponding conflict class; your reason code must never contradict your structured conflict set. CONDITION may be reported as a conflicting attribute on any decision; it never blocks a MATCH and is never an identity conflict.

MISSING-CRITICAL ATTRIBUTES RULES
- Name a dimension D in missing_critical_attributes ONLY when ALL three hold:
  (1) ELIGIBLE: D is a hard identity dimension (PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION) that the target request conveys through its MPN description, or D is PACKAGING_QUANTITY / BUNDLE under the MISSING SALES UNIT, CRITICAL condition. Dimensions the request does not convey are never decision-critical. BRAND, REVISION_OR_SUFFIX, and CONDITION are never named missing: a published difference on them is a conflicting attribute or an authority-resolved relation; an unpublished one is resolvable by inspection.
  (2) UNPINNED: the candidate side publishes no pinning value for D — no matching value and no strictly-coarser value (a coarser token pins nothing). A value published on the candidate and uncontradicted is credited, NOT missing. A published contradiction against the target is a conflict (it decides NO_MATCH or the inspection pole), not a missing attribute. A self-contradictory published pair leaves D unpinned in both directions (INTERNAL CONTRADICTION RULE).
  (3) DECISION-CRITICAL: the decision depends on D — the supplied evidence grounds equivalence at any resolution ONLY with D pinned. Where the identifier relationship is established at part-number resolution (exact published identifier, or MANUFACTURER_RELATION_AUTHORITY), attribute gaps are NOT decision-critical: the part number (or the authority-established relation) is the ground and an unpublished attribute is resolvable by inspection. Where the ground is a partial form (family+description resolution) or attribute evidence (description resolution), the unpinned request-conveyed dimension(s) are the decision-critical gaps — the alignment fails on them. Where the MISSING SALES UNIT, CRITICAL condition holds, the packaging gap is decision-critical by definition.
- Credit ALL supplied evidence on both sides (structured facts and raw observation text) BEFORE naming anything missing.
- Do not name PACKAGING_QUANTITY / BUNDLE under the non-critical condition of the COMMERCIAL SALES-UNIT RULES.

INTERNAL CONTRADICTION RULE
- If the supplied evidence contradicts ITSELF on a dimension (for example, the title states one capacity and the specification text states another, or one published field states a packaging and another contradicts it), that dimension is UNPINNED in both directions on the supplied evidence: it is neither established nor contradicted against the target. Do not pick one published side as the product's value, do not assert the corresponding conflict class, and do not return NO_MATCH on an internally contradictory dimension alone. If the dimension is a request-conveyed hard identity dimension that the contradiction leaves unpinned, it is decision-critical: return UNCERTAIN and name it in missing_critical_attributes.

DECISION RULES
- MATCH: (a) the product evidence grounds commercial equivalence at the resolution of its strongest identifier ground (IDENTITY RESOLUTION): part-number (exact identifier with identity wording; SKU equal to the target; authority-established near-miss relation), family+description (a consistent partial form plus the DISTINCTIVE-ALIGNMENT TEST), or description (no identifier, or a different retailer SKU, plus the DISTINCTIVE-ALIGNMENT TEST); (b) no published conflict on an identity dimension — hard or reviewable — exists that is not resolved by an explicit MANUFACTURER_RELATION_AUTHORITY covering that difference; (c) the sales unit does not block per the COMMERCIAL SALES-UNIT RULES (proven equal, or UNPROVEN under the non-critical condition — in which case the MATCH asserts what WHAT A MATCH ASSERTS, PRECISELY states, and nothing about unit equality or price comparability); and (d) no decision-critical dimension is missing per the MISSING-CRITICAL ATTRIBUTES RULES.
- NO_MATCH: the candidate is a different product or is not pricing-comparable as the same sales unit, grounded in PUBLISHED structured conflict classes — including the absolute packaging rule and a published accessory / role difference. A published different brand is a reviewable material difference: the decision is NO_MATCH (the default) or UNCERTAIN (where you hold the difference resolvable by inspection); it is never a MATCH. Never return NO_MATCH on missing evidence alone, on an internally contradictory dimension alone, on a customer-retrieval relation, on a different retailer SKU, or on a consistent partial form alone.
- UNCERTAIN: the evidence is insufficient or ambiguous — a decision-critical attribute is unpinned, the identifier relationship is not established without published negative evidence, a dimension is internally contradictory, a packaging cue is ambiguous, or the sales unit is critical per the COMMERCIAL SALES-UNIT RULES. If evidence is insufficient, output UNCERTAIN rather than guessing. A false MATCH is materially worse than UNCERTAIN.

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
The bounded attribute dimensions are: PRODUCT_FAMILY, GENERATION, CAPACITY, INTERFACE, FORM_FACTOR, PRODUCT_ROLE, ACCESSORY_RELATION, PACKAGING_QUANTITY, BUNDLE, BRAND, REVISION_OR_SUFFIX, CONDITION.
MATCH_AUTHORIZED_IDENTIFIER_RELATION may be used only when the CONTEXT PROVENANCE section explicitly lists MANUFACTURER_RELATION_AUTHORITY."""


# The two approved user-template annotation lines (design section 9.4).
# The 2.0 forms are the exact strings the frozen 2.0 renderer emits;
# the 2.1 forms replace them, and NOTHING ELSE in the rendering moves.
_DIC_HEADER_2_0: Final[str] = (
    "DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; "
    "you cannot override it):"
)
_DIC_HEADER_2_1: Final[str] = (
    "DETERMINISTIC IDENTITY CONTEXT (frozen deterministic layer output; "
    "the identifier facts are established; the relationship requirement "
    "line is downstream authority-tier policy, not your decision input):"
)
_REQUIREMENT_LINE_2_0: Final[str] = "- Relationship requirement: "
_REQUIREMENT_LINE_2_1: Final[str] = (
    "- Relationship requirement (downstream authority-tier policy, "
    "not your decision input): "
)


def render_v2_1_user_prompt(case: SemanticMatchCaseV2) -> str:
    """Render the exact Prompt 2.1 user prompt for one recorded V2
    input.

    The rendering is the frozen 2.0 user-prompt rendering with
    EXACTLY the two approved template annotation lines (the section-C
    header and the relationship-requirement line; design section
    9.4). Every other rendered line is byte-identical to the 2.0
    rendering for the same recorded input. Fails closed if the frozen
    2.0 renderer's output has drifted (the two 2.0 anchor lines must
    each occur exactly once).
    """
    text = render_v2_user_prompt(case)
    if text.count(_DIC_HEADER_2_0) != 1:
        raise RuntimeError(
            "the frozen 2.0 user rendering drifted: the section-C "
            "header anchor occurs "
            f"{text.count(_DIC_HEADER_2_0)} times (expected exactly "
            "once); the 2.1 annotation cannot be applied safely"
        )
    if text.count(_REQUIREMENT_LINE_2_0) != 1:
        raise RuntimeError(
            "the frozen 2.0 user rendering drifted: the relationship-"
            "requirement anchor occurs "
            f"{text.count(_REQUIREMENT_LINE_2_0)} times (expected "
            "exactly once); the 2.1 annotation cannot be applied "
            "safely"
        )
    return text.replace(
        _DIC_HEADER_2_0, _DIC_HEADER_2_1
    ).replace(_REQUIREMENT_LINE_2_0, _REQUIREMENT_LINE_2_1)


@dataclass(frozen=True)
class SemanticPromptV2_1:
    """A constructed Prompt 2.1 with version tracking.

    ``case`` is the exact recorded V2 input the prompt renders:
    together with ``SEMANTIC_PROMPT_VERSION_V2_1`` it makes the
    historical 2.1 prompt deterministically reconstructable without
    any live call. Construction fails closed on a foreign version or
    a foreign system-prompt body (a 2.1 prompt that is not the
    approved 2.1 text cannot be produced through this builder).
    """

    version: str
    system_prompt: str
    user_prompt: str
    case: SemanticMatchCaseV2

    def __post_init__(self) -> None:
        if self.version != SEMANTIC_PROMPT_VERSION_V2_1:
            raise ValueError(
                f"version must be {SEMANTIC_PROMPT_VERSION_V2_1!r}, "
                f"got {self.version!r}"
            )
        if self.system_prompt != SYSTEM_PROMPT_V2_1:
            raise ValueError(
                "system_prompt must be the approved Prompt 2.1 text; "
                "a different body cannot be constructed as a 2.1 "
                "prompt (the version is the text's identity)"
            )
        if not isinstance(self.user_prompt, str) or not self.user_prompt:
            raise TypeError("user_prompt must be a non-empty str")
        if not isinstance(self.case, SemanticMatchCaseV2):
            raise TypeError(
                "case must be SemanticMatchCaseV2, "
                f"got {type(self.case).__name__}"
            )


def build_semantic_prompt_v2_1(case: SemanticMatchCaseV2) -> SemanticPromptV2_1:
    """Build the separately versioned Prompt 2.1 for one V2 input
    case.

    The system prompt is the approved ``SYSTEM_PROMPT_V2_1``; the user
    prompt is the deterministic 2.0 rendering plus exactly the two
    approved annotation lines. This builder constructs ONLY 2.1
    prompts; the frozen 2.0 builder (``contract_v2``) is untouched
    and 2.0 prompts remain deterministically reconstructable.
    """
    return SemanticPromptV2_1(
        version=SEMANTIC_PROMPT_VERSION_V2_1,
        system_prompt=SYSTEM_PROMPT_V2_1,
        user_prompt=render_v2_1_user_prompt(case),
        case=case,
    )


# ---------------------------------------------------------------------------
# Mechanical self-consistency of the 2.1 contract data, verified once at
# import (pure data checks; no mutable state). If a future edit breaks any
# of these contracts, the module refuses to import.
# ---------------------------------------------------------------------------

if SEMANTIC_PROMPT_VERSION_V2_1 == SEMANTIC_PROMPT_VERSION_V2:
    raise RuntimeError(
        "the 2.1 prompt version must be separately versioned from the "
        "frozen 2.0 prompt version"
    )
if SYSTEM_PROMPT_V2_1 == SYSTEM_PROMPT_V2:
    raise RuntimeError(
        "the 2.1 system prompt must differ from the frozen 2.0 system "
        "prompt (a version bump without a text change is a phantom "
        "version)"
    )
if V2_1_CONTRACT_BINDING != (
    SEMANTIC_CONTRACT_VERSION_V2,
    SEMANTIC_PROMPT_VERSION_V2_1,
    SEMANTIC_INPUT_SCHEMA_VERSION_V2,
    SEMANTIC_OUTPUT_SCHEMA_VERSION_V2,
    AUTHORITY_CONTRACT_VERSION_V2_FU3,
):
    raise RuntimeError(
        "the 2.1 binding is inconsistent with its axis constants "
        "(the binding is composed from the frozen exports, never "
        "from literals)"
    )
if (
    V2_1_CONTRACT_BINDING[0] != SEMANTIC_CONTRACT_VERSION_V2
    or V2_1_CONTRACT_BINDING[2] != SEMANTIC_INPUT_SCHEMA_VERSION_V2
    or V2_1_CONTRACT_BINDING[3] != SEMANTIC_OUTPUT_SCHEMA_VERSION_V2
):
    raise RuntimeError(
        "the 2.1 binding must move ONLY the prompt axis (2.1) and the "
        "authority-contract axis (the separately versioned FU3 token); "
        "the semantic contract, input schema, and output schema axes "
        "are unchanged"
    )
if AUTHORITY_CONTRACT_VERSION_V2_FU3 == AUTHORITY_CONTRACT_VERSION_V2:
    raise RuntimeError(
        "the 2.1 binding's authority token must be the separately "
        "versioned FU3 token, not the frozen 2.0 token"
    )
