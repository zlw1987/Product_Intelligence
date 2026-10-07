"""SemanticDecisionRecord model + migration tests (S2-B / S2-B-FU1).

Covers the additive persistence structure — the universal semantic-
decision ENVELOPE row (contract-agnostic: it durably identifies any
registered semantic contract without assuming a particular one):

* the model's exact field inventory, primary key, constraints, index,
  ordering, and immutability flags (storage, not interpretation: no ad hoc
  semantic columns);
* the additive migration 0012 (create-model only, no backfill, no rewrite
  of any existing structure);
* absence semantics for legacy runs (no record is fabricated);
* cascade behavior;
* S2-B-FU1: the immutability wording is corrected — ``editable=False``
  is documented as NOT database immutability enforcement (the application
  contract is the service-owned append-only write path + uniqueness +
  digest anchor), and the row's ``schema_version`` is documented as the
  envelope format version, independent of the recorded semantic contract
  version;
* the AiAssistedReviewCandidate model is unchanged (human-review
  preservation at the model level).

Service-level semantics (persist / load / replay, digest tamper anchor,
binding verification, universal/V1 decoupling) are covered in
``tests/execution/test_semantic_decision_persistence.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from django.db import IntegrityError

from product_intelligence.domain import ResearchRequest
from product_intelligence.runs.models import (
    AiAssistedReviewCandidate,
    PriceIntelligenceSnapshot,
    ResearchRun,
    SemanticDecisionRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _cleanup():
    """Explicit per-test isolation (shared in-memory test database)."""
    yield
    SemanticDecisionRecord.objects.all().delete()
    AiAssistedReviewCandidate.objects.all().delete()
    PriceIntelligenceSnapshot.objects.all().delete()
    ResearchRun.objects.all().delete()


def _make_run(mpn: str = "ABC-123", description: str = "A test product") -> ResearchRun:
    return ResearchRun.objects.create_from_request(
        ResearchRequest(
            manufacturer_part_number=mpn, description=description
        )
    )


def _make_row(run: ResearchRun, index: int = 0, **overrides):
    defaults = dict(
        run=run,
        assessment_index=index,
        schema_version=1,
        payload={"schema_version": 1},
        payload_digest="ab" * 32,
    )
    defaults.update(overrides)
    return SemanticDecisionRecord.objects.create(**defaults)


class TestModelShape:
    EXPECTED_FIELDS = {
        "id",
        "run",
        "assessment_index",
        "schema_version",
        "payload",
        "payload_digest",
        "created_at",
    }

    def test_exact_field_inventory(self) -> None:
        assert (
            {field.name for field in SemanticDecisionRecord._meta.get_fields()}
            == self.EXPECTED_FIELDS
        )

    def test_uuid_primary_key_with_uuid4_default(self) -> None:
        from django.db import models

        pk = SemanticDecisionRecord._meta.get_field("id")
        assert pk.primary_key is True
        import uuid as uuid_mod

        assert isinstance(pk, models.UUIDField)
        assert pk.default == uuid_mod.uuid4
        assert pk.editable is False

    def test_storage_not_interpretation_no_ad_hoc_semantic_columns(self) -> None:
        """The artifact's semantic fields all live in the opaque payload;
        the model carries no scattered semantic authority columns."""
        field_names = {
            field.name for field in SemanticDecisionRecord._meta.get_fields()
        }
        forbidden = {
            "decision",
            "confidence",
            "tier",
            "authority_tier",
            "provider",
            "actual_provider",
            "model",
            "actual_model",
            "prompt_version",
            "evaluation_state",
            "reason_code",
            "matched_attributes",
            "conflict_classes",
            "source_url",
            "target_mpn",
            "candidate_title",
            "error_type",
            "fallback_used",
            "input_digest",
            "output_digest",
        }
        assert not (field_names & forbidden), (
            f"scattered semantic columns found: {sorted(field_names & forbidden)}"
        )

    def test_unique_constraint_per_run_assessment(self) -> None:
        from django.db import models

        constraints = {
            c.name: c for c in SemanticDecisionRecord._meta.constraints
        }
        uc = constraints[
            "semantic_decision_record_unique_per_run_assessment"
        ]
        assert isinstance(uc, models.UniqueConstraint)
        assert set(uc.fields) == {"run", "assessment_index"}

    def test_check_constraints(self) -> None:
        constraints = {
            c.name: c for c in SemanticDecisionRecord._meta.constraints
        }
        assert "semantic_decision_record_schema_version_gte_1" in constraints
        assert (
            "semantic_decision_record_payload_digest_sha256_hex"
            in constraints
        )

    def test_index_and_ordering(self) -> None:
        indexes = {index.name for index in SemanticDecisionRecord._meta.indexes}
        assert "sdr_run_assessment_idx" in indexes
        assert SemanticDecisionRecord._meta.ordering == [
            "run",
            "assessment_index",
        ]

    def test_artifact_columns_are_immutable(self) -> None:
        for name in (
            "assessment_index",
            "schema_version",
            "payload",
            "payload_digest",
            "created_at",
        ):
            field = SemanticDecisionRecord._meta.get_field(name)
            assert field.editable is False, name

    def test_reverse_accessor_on_run(self) -> None:
        run = _make_run()
        _make_row(run)
        assert run.semantic_decision_records.count() == 1


class TestConstraintsEnforced:
    def test_duplicate_run_assessment_rejected(self) -> None:
        run = _make_run()
        _make_row(run, index=3)
        with pytest.raises(IntegrityError):
            _make_row(run, index=3)

    def test_different_index_allowed(self) -> None:
        run = _make_run()
        _make_row(run, index=0)
        row = _make_row(run, index=1)
        assert row.assessment_index == 1

    def test_schema_version_zero_rejected(self) -> None:
        run = _make_run()
        with pytest.raises(IntegrityError):
            _make_row(run, schema_version=0)

    def test_invalid_payload_digest_rejected(self) -> None:
        run = _make_run()
        with pytest.raises(IntegrityError):
            _make_row(run, payload_digest="NOT-A-DIGEST")
        with pytest.raises(IntegrityError):
            _make_row(run, payload_digest="AB" * 32)  # uppercase hex


class TestLegacyAndCascade:
    def test_legacy_run_has_no_record_and_none_is_fabricated(self) -> None:
        """A run created before S2-B simply has no record. Absence means
        'legacy semantic provenance unavailable under V2' — not NO_MATCH,
        not NOT_EVALUATED, not an AI failure. Nothing fabricates a row."""
        run = _make_run()
        assert run.semantic_decision_records.count() == 0
        assert SemanticDecisionRecord.objects.filter(run=run).count() == 0
        # A snapshot-only run (the legacy shape) stays record-free.
        PriceIntelligenceSnapshot.objects.create(
            run=run, schema_version=1, payload={"request": {}, "assessments": [], "buckets": [], "exclusions": [], "verification_status": "OK"}
        )
        assert run.semantic_decision_records.count() == 0

    def test_cascade_delete_with_run(self) -> None:
        run = _make_run()
        row = _make_row(run)
        row_id = row.id
        run.delete()
        assert SemanticDecisionRecord.objects.filter(id=row_id).count() == 0


class TestEnvelopeDecouplingWording:
    """S2-B-FU1: the model documentation states the corrected immutability
    contract and the independent version axes."""

    @classmethod
    def setup_class(cls) -> None:
        cls.doc = SemanticDecisionRecord.__doc__ or ""

    def test_editable_false_is_not_documented_as_db_enforcement(self) -> None:
        """The audit correction: ``editable=False`` "enforcing"
        immutability is wrong — it is only a forms-mapping hint. The docs
        must say so, and must name the application contract instead."""
        assert "NOT database immutability enforcement" in self.doc
        assert "application contract" in self.doc.lower() or (
            "APPLICATION contract" in self.doc
        )
        # The stale claim is gone.
        assert "Immutability is\n        enforced" not in self.doc.replace("\r", "")
        assert "Immutability is enforced" not in self.doc

    def test_application_contract_is_the_write_path_uniqueness_digest(self) -> None:
        # The corrected wording names the three application-level pillars.
        assert "append-only write path" in self.doc
        assert "uniqueness constraint" in self.doc
        assert "digest anchor" in self.doc
        # Out-of-band mutation is detected / fails closed, not prevented
        # by the database.
        assert "Out-of-band mutation" in self.doc
        assert "fails closed" in self.doc

    def test_row_schema_version_is_the_envelope_axis_not_the_semantic_contract(
        self,
    ) -> None:
        # The docs make the independent version axes explicit.
        assert "ENVELOPE format version" in self.doc
        assert "INDEPENDENT of the semantic contract version" in self.doc

    def test_future_contract_reuses_the_row_without_migration(self) -> None:
        # A future semantic contract registers a new adapter; the row (and
        # the migration) do not change for that reason.
        assert "no model change, no new" in self.doc


class TestMigration:
    MIGRATION_PATH = (
        REPO_ROOT
        / "product_intelligence"
        / "runs"
        / "migrations"
        / "0012_semantic_decision_record.py"
    )

    def test_migration_exists(self) -> None:
        assert self.MIGRATION_PATH.is_file()

    def test_migration_is_additive_create_model_only(self) -> None:
        tree = ast.parse(self.MIGRATION_PATH.read_text(encoding="utf-8"))
        ops = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", "")
            if name in (
                "CreateModel",
                "AddField",
                "AlterField",
                "RemoveField",
                "AlterModelOptions",
                "AddConstraint",
                "AlterIndexTogether",
                "RunPython",
                "RunSQL",
            ):
                ops.append(name)
        assert ops == ["CreateModel"], (
            "the S2-B migration must be a single additive CreateModel with "
            f"no rewrites, backfills, or data operations; got {ops}"
        )

    def test_migration_creates_semantic_decision_record(self) -> None:
        source = self.MIGRATION_PATH.read_text(encoding="utf-8")
        assert "CreateModel" in source
        assert "SemanticDecisionRecord" in source
        assert "0011_researchfxsnapshot_acquisition_fxobservationstore" in source

    def test_migration_performs_no_semantic_backfill(self) -> None:
        source = self.MIGRATION_PATH.read_text(encoding="utf-8")
        assert "RunPython" not in source
        assert "RunSQL" not in source

    def test_migration_applied_to_test_database(self) -> None:
        """The session test database is created by running every migration
        (tests/conftest.py): the new table must exist here."""
        from django.db import connection

        table = SemanticDecisionRecord._meta.db_table
        with connection.cursor() as cursor:
            # table is Django's own trusted constant (never user input),
            # so direct interpolation is safe here; the raw sqlite_master
            # query cannot use ORM parameter binding.
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{table}'"
            )
            assert cursor.fetchone() is not None

    def test_ai_assisted_review_candidate_model_unchanged(self) -> None:
        """Human-review preservation: the review candidate model keeps its
        exact frozen field inventory (S2-B adds a sibling, not a field)."""
        expected = {
            "id",
            "run",
            "assessment_index",
            "source_url",
            "target_mpn",
            "target_description",
            "candidate_title",
            "candidate_mpn_field",
            "candidate_sku",
            "candidate_specs",
            "evidence_source",
            "semantic_confidence",
            "semantic_reason_code",
            "semantic_matched_attributes",
            "semantic_conflicting_attributes",
            "actual_provider",
            "actual_model",
            "prompt_version",
            "review_state",
            "created_at",
            "reviewed_at",
        }
        assert (
            {
                field.name
                for field in AiAssistedReviewCandidate._meta.get_fields()
            }
            == expected
        )
