"""Product Specification Framework (PRODUCT-INTEL.6A).

Deterministic, caller-independent, Django-free specification resolution
framework. Defines seven canonical contracts and one resolver:

    SpecificationDefinition
    SpecificationValue
    SpecificationObservation
    NormalizedSpecificationObservation
    SpecificationResolution
    CategorySchema
    ProductSpecificationSet

plus the resolver function:

    resolve_specification(...)

This module is pure: no side effects, no state beyond its inputs. Same inputs
always produce the same outputs. No extraction, no LLM call, no persistence,
no network access, no category-specific fields.

The framework mirrors the project's existing evidence-first pattern:
    SpecificationObservation  (raw evidence)
        ->
    NormalizedSpecificationObservation  (canonical or issue)
        ->
    SpecificationResolution  (deterministic four-state resolution)
        ->
    ProductSpecificationSet  (complete per-identity per-schema state)

Identity binding follows the existing authority chain:
    ProductIdentity.is_established  (EXACT or NORMALIZED_EXACT)
    ->
    SpecificationObservation requires established identity
    ->
    SpecificationResolution self-auditing over one identity/spec pair
    ->
    ProductSpecificationSet completeness invariants reject cross-product evidence
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from product_intelligence.domain.models import ProductIdentity


# ---------------------------------------------------------------------------
# Value kinds
# ---------------------------------------------------------------------------


class SpecificationValueKind(str, Enum):
    """The canonical value kind for a specification definition.

    Exactly four kinds. No speculative extensions:

    TEXT — any canonical text value
    DECIMAL — numeric value using Decimal only (never float)
    BOOLEAN — true/false
    ENUM — one value from a defined allowed set
    """

    TEXT = "TEXT"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"


# ---------------------------------------------------------------------------
# Source authority
# ---------------------------------------------------------------------------


class SourceAuthority(str, Enum):
    """The authority tier of the evidence source.

    AUTHORITATIVE — manufacturer-controlled or otherwise explicitly
        authoritative product source.
    SECONDARY — retailer / distributor / marketplace / other supporting
        source.

    6A does NOT infer authority from hostname or URL. A later evidence-
    acquisition policy supplies the authority classification.
    """

    AUTHORITATIVE = "AUTHORITATIVE"
    SECONDARY = "SECONDARY"


# ---------------------------------------------------------------------------
# Private evidence-derived resolution helper (§22.0 evidence binding)
# ---------------------------------------------------------------------------


def _derive_resolution_from_evidence(
    evidence: tuple[NormalizedSpecificationObservation, ...],
) -> tuple[ResolutionState, SpecificationValue | None]:
    """Deterministically derive the expected (state, resolved_value) from evidence.

    This is the single source of truth for state/value derivation.
    Both resolve_specification() and SpecificationResolution.__post_init__()
    use this function so a manually constructed SpecificationResolution
    is mechanically bound to the exact evidence-derived result.

    Rules (frozen §22.0):
        0 usable values  -> UNKNOWN, resolved_value = None
        1 unique value + >=1 AUTHORITATIVE -> VERIFIED, resolved_value = value
        1 unique value + SECONDARY-only   -> UNVERIFIED, resolved_value = value
        >1 unique values  -> CONFLICT, resolved_value = None
    """
    usable = tuple(obs for obs in evidence if obs.is_usable)

    if not usable:
        return ResolutionState.UNKNOWN, None

    # Collect unique canonical values
    unique_values: list[SpecificationValue] = []
    for obs in usable:
        sv = obs.canonical_value
        if sv is None:
            continue
        found = False
        for existing in unique_values:
            if existing.value == sv.value and type(existing.value) is type(sv.value):
                found = True
                break
        if not found:
            unique_values.append(sv)

    if len(unique_values) > 1:
        return ResolutionState.CONFLICT, None

    # Exactly one unique value — check authority
    has_authoritative = any(
        obs.observation.source_authority is SourceAuthority.AUTHORITATIVE
        for obs in usable
    )

    if has_authoritative:
        return ResolutionState.VERIFIED, unique_values[0]
    else:
        return ResolutionState.UNVERIFIED, unique_values[0]


# ---------------------------------------------------------------------------
# Resolution states
# ---------------------------------------------------------------------------


class ResolutionState(str, Enum):
    """The four states of specification resolution.

    UNKNOWN — zero usable canonical values
    VERIFIED — one unique canonical value with >= 1 AUTHORITATIVE support
    UNVERIFIED — one unique canonical value with SECONDARY-only support
    CONFLICT — more than one unique canonical value
    """

    UNKNOWN = "UNKNOWN"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"


# ---------------------------------------------------------------------------
# SpecificationDefinition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationDefinition:
    """What a specification is — a definition/schema concept, not an actual value.

    A SpecificationDefinition describes the shape of one specification attribute:
    its stable machine key, human-readable label, value kind, optional canonical
    unit (for DECIMAL), and allowed values (for ENUM).

    This is a schema element, not a product's actual specification value.
    """

    key: str
    label: str
    value_kind: SpecificationValueKind
    unit: str | None = None
    allowed_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("key must be a non-empty string")
        object.__setattr__(self, "key", self.key.strip())

        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a non-empty string")
        object.__setattr__(self, "label", self.label.strip())

        if not isinstance(self.value_kind, SpecificationValueKind):
            raise TypeError(
                f"value_kind must be a SpecificationValueKind, got "
                f"{type(self.value_kind).__name__}"
            )

        if self.unit is not None:
            if not isinstance(self.unit, str) or not self.unit.strip():
                raise ValueError("unit must be a non-empty string or None")
            object.__setattr__(self, "unit", self.unit.strip())

        if not isinstance(self.allowed_values, tuple):
            raise TypeError("allowed_values must be a tuple of strings")
        for v in self.allowed_values:
            if not isinstance(v, str):
                raise TypeError(
                    f"allowed_values must contain only strings, got {type(v).__name__}"
                )
        object.__setattr__(self, "allowed_values", tuple(v.strip() for v in self.allowed_values))

        # ENUM must have allowed values
        if self.value_kind is SpecificationValueKind.ENUM and not self.allowed_values:
            raise ValueError(
                "ENUM specification requires non-empty allowed_values"
            )

    def validate_canonical_value(self, value: Any) -> bool:
        """Check whether a canonical value is valid for this definition.

        This is the definition/value compatibility check from §22.0.1.
        """
        if self.value_kind is SpecificationValueKind.TEXT:
            return isinstance(value, str)

        if self.value_kind is SpecificationValueKind.DECIMAL:
            # Must be Decimal, never float, and must be finite
            # (NaN, sNaN, Infinity, -Infinity all rejected)
            if type(value) is not Decimal:
                return False
            if not value.is_finite():
                return False
            return True

        if self.value_kind is SpecificationValueKind.BOOLEAN:
            return isinstance(value, bool)

        if self.value_kind is SpecificationValueKind.ENUM:
            return isinstance(value, str) and value in self.allowed_values

        return False


# ---------------------------------------------------------------------------
# SpecificationValue
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationValue:
    """A CANONICAL specification value — not raw external text.

    A SpecificationValue represents a normalized, canonical value that has
    been resolved from raw evidence. It is valid only when compatible with
    its associated SpecificationDefinition.

    Examples:
        Decimal("3.84") for a DECIMAL capacity spec in TB
        "U.3" for a TEXT interface connector spec
        True for a BOOLEAN spec
    """

    value: str | Decimal | bool

    def __post_init__(self) -> None:
        if not isinstance(self.value, (str, Decimal, bool)):
            raise TypeError(
                f"SpecificationValue.value must be str, Decimal, or bool, "
                f"got {type(self.value).__name__}"
            )


# ---------------------------------------------------------------------------
# SpecificationObservation — Raw Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationObservation:
    """Raw evidence: a source published this about this specification.

    Binds to:
        - one established ProductIdentity (checked at construction)
        - one SpecificationDefinition

    Preserves full provenance: source name, URL, retrieval timestamp,
    raw value, optional raw reference/locator, and source authority.

    Raw evidence remains raw. An observation means "a source said this",
    not "therefore this is true."
    """

    product_identity: ProductIdentity
    definition: SpecificationDefinition
    source_name: str
    source_url: str
    retrieved_at: datetime
    raw_value: str
    source_authority: SourceAuthority
    raw_reference: str | None = None

    def __post_init__(self) -> None:
        # Identity must be established
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "SpecificationObservation requires an established ProductIdentity "
                f"(match_type={self.product_identity.match_type.value}); "
                f"unestablished identities cannot support specification evidence. "
                "Specifications do not establish identity."
            )

        # Definition must be valid
        if not isinstance(self.definition, SpecificationDefinition):
            raise TypeError(
                f"definition must be a SpecificationDefinition, got "
                f"{type(self.definition).__name__}"
            )

        # Source name
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("source_name must be a non-empty string")
        object.__setattr__(self, "source_name", self.source_name.strip())

        # Source URL
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise ValueError("source_url must be a non-empty string")
        object.__setattr__(self, "source_url", self.source_url.strip())

        # Retrieved at must be timezone-aware
        if not isinstance(self.retrieved_at, datetime):
            raise TypeError(
                f"retrieved_at must be a datetime, got {type(self.retrieved_at).__name__}"
            )
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")

        # Raw value
        if not isinstance(self.raw_value, str):
            raise TypeError(
                f"raw_value must be a string, got {type(self.raw_value).__name__}"
            )
        # Interior of raw value is preserved exactly — only strip if it's empty
        object.__setattr__(self, "raw_value", self.raw_value or None)
        if self.raw_value is None:
            raise ValueError("raw_value must not be empty")

        # Source authority
        if not isinstance(self.source_authority, SourceAuthority):
            raise TypeError(
                f"source_authority must be a SourceAuthority, got "
                f"{type(self.source_authority).__name__}"
            )

        # Raw reference
        if self.raw_reference is not None:
            if not isinstance(self.raw_reference, str):
                raise TypeError(
                    f"raw_reference must be a string or None, got "
                    f"{type(self.raw_reference).__name__}"
                )
            object.__setattr__(
                self, "raw_reference", self.raw_reference.strip() or None
            )


# ---------------------------------------------------------------------------
# NormalizedSpecificationObservation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizedSpecificationObservation:
    """A SpecificationObservation with either a canonical value or a normalization issue.

    Mirrors the project's 3A -> 3B evidence-first pattern. Preserves the
    original observation with full provenance.

    Carries EXACTLY ONE of:
        - a valid canonical SpecificationValue (valid for the original
          SpecificationDefinition)
        - no canonical value + explicit normalization issue/reason

    An ambiguous or unparseable raw value does NOT silently become a fact.
    Issue-only observations are preserved as audit evidence.

    Impossible states (both canonical + issue, or neither) are rejected
    at construction.
    """

    observation: SpecificationObservation
    canonical_value: SpecificationValue | None = None
    normalization_issue: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.observation, SpecificationObservation):
            raise TypeError(
                f"observation must be a SpecificationObservation, got "
                f"{type(self.observation).__name__}"
            )

        # Exactly one of canonical_value or normalization_issue must be present
        has_canonical = self.canonical_value is not None
        has_issue = self.normalization_issue is not None

        if has_canonical and has_issue:
            raise ValueError(
                "NormalizedSpecificationObservation must have exactly one of "
                "canonical_value or normalization_issue, not both"
            )
        if not has_canonical and not has_issue:
            raise ValueError(
                "NormalizedSpecificationObservation must have exactly one of "
                "canonical_value or normalization_issue, not neither"
            )

        # If canonical value present, validate against definition
        if has_canonical:
            if not isinstance(self.canonical_value, SpecificationValue):
                raise TypeError(
                    f"canonical_value must be a SpecificationValue, got "
                    f"{type(self.canonical_value).__name__}"
                )
            if not self.observation.definition.validate_canonical_value(
                self.canonical_value.value
            ):
                raise ValueError(
                    f"canonical_value ({self.canonical_value.value!r}) is not valid "
                    f"for definition '{self.observation.definition.key}' "
                    f"(kind={self.observation.definition.value_kind.value})"
                )

        # If normalization issue present, validate
        if has_issue:
            if not isinstance(self.normalization_issue, str):
                raise TypeError(
                    f"normalization_issue must be a string, got "
                    f"{type(self.normalization_issue).__name__}"
                )
            if not self.normalization_issue.strip():
                raise ValueError("normalization_issue must be a non-empty string")
            object.__setattr__(
                self, "normalization_issue", self.normalization_issue.strip()
            )

    @property
    def is_usable(self) -> bool:
        """Whether this observation provides a usable canonical value.

        Issue-only observations are preserved as evidence but are NOT usable
        canonical evidence for value resolution.
        """
        return self.canonical_value is not None


# ---------------------------------------------------------------------------
# SpecificationResolution — Four-State Deterministic Resolver
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpecificationResolution:
    """Deterministic resolution of one specification for one established identity.

    Represents the complete resolved state of exactly one SpecificationDefinition
    for exactly one established ProductIdentity, from a given collection of
    NormalizedSpecificationObservation evidence.

    Self-auditing invariants:
        - Every input normalized observation belongs to the same
          established ProductIdentity as the resolution.
        - Every input normalized observation belongs to the same
          SpecificationDefinition as the resolution.
        - Cross-product evidence is rejected.
        - Cross-specification evidence is rejected.
        - Evidence collection is preserved (no silent dropping).
        - Issue-only observations are preserved as audit evidence.

    Resolution states:
        UNKNOWN — zero usable canonical values, resolved_value = None
        VERIFIED — one unique canonical value + >= 1 AUTHORITATIVE, resolved_value = value
        UNVERIFIED — one unique canonical value + SECONDARY-only, resolved_value = value
        CONFLICT — >1 unique canonical values, resolved_value = None

    No majority voting. No source-count weighting. No authoritative-wins-conflict.
    """

    product_identity: ProductIdentity
    definition: SpecificationDefinition
    state: ResolutionState
    resolved_value: SpecificationValue | None
    evidence: tuple[NormalizedSpecificationObservation, ...]

    def __post_init__(self) -> None:
        # Identity must be established
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "SpecificationResolution requires an established ProductIdentity"
            )

        if not isinstance(self.definition, SpecificationDefinition):
            raise TypeError(
                f"definition must be a SpecificationDefinition, got "
                f"{type(self.definition).__name__}"
            )

        if not isinstance(self.state, ResolutionState):
            raise TypeError(
                f"state must be a ResolutionState, got "
                f"{type(self.state).__name__}"
            )

        # resolved_value type check
        if self.resolved_value is not None:
            if not isinstance(self.resolved_value, SpecificationValue):
                raise TypeError(
                    f"resolved_value must be a SpecificationValue or None, got "
                    f"{type(self.resolved_value).__name__}"
                )

        # Evidence must be a tuple
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be a tuple of NormalizedSpecificationObservation")
        for obs in self.evidence:
            if not isinstance(obs, NormalizedSpecificationObservation):
                raise TypeError(
                    f"evidence must contain only NormalizedSpecificationObservation, "
                    f"got {type(obs).__name__}"
                )

        # Self-auditing: every evidence observation must match identity and definition
        for obs in self.evidence:
            if obs.observation.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product evidence rejected: evidence observation's "
                    f"identity does not match resolution identity. "
                    f"Identity binding invariant violated."
                )
            if obs.observation.definition is not self.definition:
                raise ValueError(
                    "Cross-specification evidence rejected: evidence observation's "
                    f"definition '{obs.observation.definition.key}' does not match "
                    f"resolution definition '{self.definition.key}'. "
                    f"Definition binding invariant violated."
                )

        # BLOCKER A FIX: derive expected state/value from evidence
        # This binds the constructor to the evidence-derived result.
        # A manually constructed SpecificationResolution with fabricated
        # state/value is mechanically rejected.
        expected_state, expected_value = _derive_resolution_from_evidence(
            self.evidence
        )

        if self.state is not expected_state:
            raise ValueError(
                f"SpecificationResolution state mismatch: evidence derives "
                f"{expected_state.value}, but supplied state is {self.state.value}. "
                f"State must be derived from evidence, not fabricated."
            )

        if self.resolved_value is not None and expected_value is not None:
            if self.resolved_value.value != expected_value.value or \
               type(self.resolved_value.value) is not type(expected_value.value):
                raise ValueError(
                    f"SpecificationResolution resolved_value mismatch: evidence derives "
                    f"{expected_value.value!r} ({type(expected_value.value).__name__}), "
                    f"but supplied value is {self.resolved_value.value!r} "
                    f"({type(self.resolved_value.value).__name__}). "
                    f"Resolved value must match the evidence-derived value."
                )
        elif self.resolved_value is None and expected_value is not None:
            raise ValueError(
                f"SpecificationResolution resolved_value mismatch: evidence derives "
                f"{expected_value.value!r}, but supplied value is None. "
                f"Resolved value must match the evidence-derived value."
            )
        elif self.resolved_value is not None and expected_value is None:
            raise ValueError(
                f"SpecificationResolution resolved_value mismatch: evidence derives "
                f"no resolved value (expected_value=None for {expected_state.value}), "
                f"but supplied value is {self.resolved_value.value!r}. "
                f"Resolved value must match the evidence-derived value."
            )

    @property
    def usable_evidence(self) -> tuple[NormalizedSpecificationObservation, ...]:
        """Usable canonical observations (those with a canonical value).

        Issue-only observations are NOT included here for voting purposes,
        but they remain in self.evidence as audit trail.
        """
        return tuple(obs for obs in self.evidence if obs.is_usable)

    @property
    def issue_only_evidence(self) -> tuple[NormalizedSpecificationObservation, ...]:
        """Observations that failed normalization but are preserved as evidence."""
        return tuple(obs for obs in self.evidence if not obs.is_usable)


# ---------------------------------------------------------------------------
# resolve_specification()
# ---------------------------------------------------------------------------


def resolve_specification(
    product_identity: ProductIdentity,
    definition: SpecificationDefinition,
    observations: tuple[NormalizedSpecificationObservation, ...],
) -> SpecificationResolution:
    """Deterministic four-state specification resolution.

    Operates on observations for exactly one established ProductIdentity
    and one SpecificationDefinition.

    Cross-product evidence (mixed identities): REJECTED.
    Cross-specification evidence (mixed definitions): REJECTED.

    Returns a SpecificationResolution preserving the complete normalized
    evidence tuple.

    Rules:
        0 usable values  -> UNKNOWN, resolved_value = None
        1 unique value + >=1 AUTHORITATIVE -> VERIFIED, resolved_value = value
        1 unique value + SECONDARY-only   -> UNVERIFIED, resolved_value = value
        >1 unique values  -> CONFLICT, resolved_value = None

    No majority voting. 9 secondary A + 1 authoritative B = CONFLICT.
    """
    # Validate identity
    if not isinstance(product_identity, ProductIdentity):
        raise TypeError(
            f"product_identity must be a ProductIdentity, got "
            f"{type(product_identity).__name__}"
        )
    if not product_identity.is_established:
        raise ValueError(
            "resolve_specification requires an established ProductIdentity; "
            f"got match_type={product_identity.match_type.value}. "
            "Specifications do not establish identity."
        )

    # Validate definition
    if not isinstance(definition, SpecificationDefinition):
        raise TypeError(
            f"definition must be a SpecificationDefinition, got "
            f"{type(definition).__name__}"
        )

    # Validate observations tuple
    if not isinstance(observations, tuple):
        raise TypeError("observations must be a tuple of NormalizedSpecificationObservation")

    for obs in observations:
        if not isinstance(obs, NormalizedSpecificationObservation):
            raise TypeError(
                f"observations must contain only NormalizedSpecificationObservation, "
                f"got {type(obs).__name__}"
            )

    # Reject cross-product evidence
    for obs in observations:
        if obs.observation.product_identity is not product_identity:
            raise ValueError(
                "Cross-product evidence rejected: observation's ProductIdentity "
                "does not match the resolution's ProductIdentity. "
                "All evidence must belong to the same established identity."
            )

    # Reject cross-specification evidence
    for obs in observations:
        if obs.observation.definition is not definition:
            raise ValueError(
                "Cross-specification evidence rejected: observation's "
                f"SpecificationDefinition ('{obs.observation.definition.key}') "
                f"does not match the resolution's definition ('{definition.key}'). "
                "All evidence must belong to the same specification."
            )

    # Derive state and resolved_value from evidence using the shared helper
    state, resolved_value = _derive_resolution_from_evidence(observations)

    return SpecificationResolution(
        product_identity=product_identity,
        definition=definition,
        state=state,
        resolved_value=resolved_value,
        evidence=observations,
    )


# ---------------------------------------------------------------------------
# CategorySchema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategorySchema:
    """A versioned grouping of specification definitions for one product category.

    Category-neutral mechanism. 6A defines the structure; 6B creates the
    first real category schema. No category-specific fields belong in 6A.

    Definition keys must be unique within the schema.
    Mapping key must equal SpecificationDefinition.key after canonical strip.
    The definitions mapping is immutable (types.MappingProxyType) after
    construction to prevent post-construction mutation.
    """

    schema_id: str
    schema_version: str
    label: str
    definitions: Mapping[str, SpecificationDefinition]

    def __post_init__(self) -> None:
        # schema_id
        if not isinstance(self.schema_id, str) or not self.schema_id.strip():
            raise ValueError("schema_id must be a non-empty string")
        object.__setattr__(self, "schema_id", self.schema_id.strip())

        # schema_version
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("schema_version must be a non-empty string")
        object.__setattr__(self, "schema_version", self.schema_version.strip())

        # label
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a non-empty string")
        object.__setattr__(self, "label", self.label.strip())

        # definitions — must be a mapping
        if not isinstance(self.definitions, dict):
            raise TypeError("definitions must be a dict[str, SpecificationDefinition]")

        seen_keys: set[str] = set()
        # Defensive copy so caller-owned dict cannot mutate the schema
        normalized_defs: dict[str, SpecificationDefinition] = {}
        for key, defn in self.definitions.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"Definition key must be a non-empty string, got {key!r}")
            if not isinstance(defn, SpecificationDefinition):
                raise TypeError(
                    f"Definition for key '{key}' must be a SpecificationDefinition, "
                    f"got {type(defn).__name__}"
                )
            stripped_key = key.strip()

            # BLOCKER C: mapping key MUST equal SpecificationDefinition.key
            if stripped_key != defn.key:
                raise ValueError(
                    f"Schema mapping key '{stripped_key}' does not equal "
                    f"SpecificationDefinition.key '{defn.key}'. "
                    f"The dict key and the definition's own key must be the same "
                    f"after canonical whitespace handling."
                )

            if stripped_key in seen_keys:
                raise ValueError(
                    f"Duplicate definition key '{stripped_key}' in schema. "
                    "Definition keys must be unique within a CategorySchema."
                )
            seen_keys.add(stripped_key)
            normalized_defs[stripped_key] = defn

        # Additional check: definitions' own keys must also be unique
        defn_keys = {d.key for d in normalized_defs.values()}
        if len(defn_keys) != len(normalized_defs):
            raise ValueError(
                "SpecificationDefinition keys are not unique within the schema. "
                "No two definitions may claim the same stable machine key."
            )

        # BLOCKER B: immutable mapping via MappingProxyType (defensive copy)
        object.__setattr__(
            self, "definitions",
            MappingProxyType(normalized_defs)
        )


# ---------------------------------------------------------------------------
# ProductSpecificationSet
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductSpecificationSet:
    """Complete resolved specification state for one product under one category schema.

    Represents exactly one established ProductIdentity under exactly one
    CategorySchema, with exactly one SpecificationResolution for every
    definition in the schema.

    Completeness invariants (fail-closed):
        A. Exactly ONE SpecificationResolution per schema definition.
           UNKNOWN is explicit, not implied by absence.
        B. No resolution for a definition outside the schema.
        C. No duplicate resolution for the same definition key.
        D. Every resolution's ProductIdentity equals the set's identity.
        E. Every resolution's SpecificationDefinition corresponds to the
           exact definition from the CategorySchema for that key.

    Cross-product/specification failure modes all fail closed.
    Resolution keys are canonical (stripped) and the mapping is immutable
    after construction.
    """

    product_identity: ProductIdentity
    category_schema: CategorySchema
    resolutions: Mapping[str, SpecificationResolution]

    def __post_init__(self) -> None:
        # Identity must be established
        if not isinstance(self.product_identity, ProductIdentity):
            raise TypeError(
                f"product_identity must be a ProductIdentity, got "
                f"{type(self.product_identity).__name__}"
            )
        if not self.product_identity.is_established:
            raise ValueError(
                "ProductSpecificationSet requires an established ProductIdentity; "
                f"got match_type={self.product_identity.match_type.value}. "
                "Specifications do not establish identity."
            )

        # CategorySchema
        if not isinstance(self.category_schema, CategorySchema):
            raise TypeError(
                f"category_schema must be a CategorySchema, got "
                f"{type(self.category_schema).__name__}"
            )

        # Resolutions must be a dict
        if not isinstance(self.resolutions, dict):
            raise TypeError("resolutions must be a dict[str, SpecificationResolution]")

        schema_def_keys = set(self.category_schema.definitions.keys())
        resolution_keys: set[str] = set()
        # Defensive copy so caller-owned dict cannot mutate the set
        normalized_resolutions: dict[str, SpecificationResolution] = {}

        for key, resolution in self.resolutions.items():
            if not isinstance(key, str):
                raise TypeError(f"Resolution key must be a string, got {type(key).__name__}")
            if not isinstance(resolution, SpecificationResolution):
                raise TypeError(
                    f"Resolution for key '{key}' must be a SpecificationResolution, "
                    f"got {type(resolution).__name__}"
                )

            stripped_key = key.strip()

            # BLOCKER C: canonical key enforcement — key must match a schema definition
            # and the resolution's definition must correspond to that schema definition
            if stripped_key not in schema_def_keys:
                raise ValueError(
                    f"Resolution key '{stripped_key}' is not a definition in the "
                    f"CategorySchema. Schema definitions: {sorted(schema_def_keys)}. "
                    "No resolution may exist for a definition outside the CategorySchema."
                )

            # C. No duplicate resolution key
            if stripped_key in resolution_keys:
                raise ValueError(
                    f"Duplicate resolution key '{stripped_key}'. "
                    "No duplicate resolution for the same specification key."
                )
            resolution_keys.add(stripped_key)

            # D. Every resolution's identity must match the set's identity
            if resolution.product_identity is not self.product_identity:
                raise ValueError(
                    "Cross-product resolution rejected: resolution's ProductIdentity "
                    "does not match the ProductSpecificationSet's ProductIdentity. "
                    "All resolutions must belong to the same established identity."
                )

            # E. Resolution's definition must correspond to the exact schema definition
            schema_def = self.category_schema.definitions[stripped_key]
            if resolution.definition is not schema_def:
                raise ValueError(
                    f"Resolution for '{stripped_key}' has a SpecificationDefinition "
                    f"that does not match the CategorySchema's definition for that key. "
                    "Every resolution's definition must correspond to the exact "
                    "CategorySchema definition it represents."
                )

            # Store with canonical (stripped) key
            normalized_resolutions[stripped_key] = resolution

        # A. Every schema definition must have exactly one resolution
        missing = schema_def_keys - resolution_keys
        if missing:
            raise ValueError(
                f"Missing resolutions for schema definitions: {sorted(missing)}. "
                "Every SpecificationDefinition in the CategorySchema must have "
                "exactly one SpecificationResolution. UNKNOWN must be explicit."
            )

        # Extra resolutions (not in schema)
        extra = resolution_keys - schema_def_keys
        if extra:
            raise ValueError(
                f"Extra resolutions not in schema: {sorted(extra)}. "
                "No resolution may exist for a definition outside the CategorySchema."
            )

        # BLOCKER B: immutable mapping via MappingProxyType (defensive copy)
        object.__setattr__(
            self, "resolutions",
            MappingProxyType(normalized_resolutions)
        )
