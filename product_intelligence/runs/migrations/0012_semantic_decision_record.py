# Generated migration for SemanticDecisionRecord (PRODUCT-INTEL.SEMANTIC-
# AUTHORITY-V2-S2-B): additive persistence of the semantic-decision
# artifact. One record per (run, assessment_index); opaque versioned
# payload (schema owned by research/semantic_decision_codec.py) with a
# separate canonical-digest tamper anchor. No backfill, no semantic
# rewrite, no change to any existing model, snapshot, or review state.

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0011_researchfxsnapshot_acquisition_fxobservationstore'),
    ]

    operations = [
        migrations.CreateModel(
            name='SemanticDecisionRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Opaque durable record identity (application-generated UUID4).', primary_key=True, serialize=False)),
                ('assessment_index', models.PositiveSmallIntegerField(editable=False, help_text="Stable binding: the position of the assessed candidate in the ordered assessments tuple of this run's PriceIntelligenceSnapshot (the same binding semantics as AiAssistedReviewCandidate.assessment_index).")),
                ('schema_version', models.PositiveSmallIntegerField(editable=False, help_text='Codec version that produced the payload. The only supported value is 1 (research.semantic_decision_codec). An unsupported version fails closed on decode.')),
                ('payload', models.JSONField(editable=False, help_text='Opaque versioned codec-encoded SemanticDecisionRecord artifact (research/semantic_decision_codec.py). Storage, not interpretation: the schema is owned by the codec.')),
                ('payload_digest', models.CharField(editable=False, help_text='Canonical SHA-256 digest of the payload, computed at write time by the persistence service and stored separately as the whole-artifact tamper anchor. Verified on every read; a mismatch fails closed.', max_length=64)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, help_text='When this record row was persisted (not the evaluation instants, which are inside the payload).')),
                ('run', models.ForeignKey(help_text='The research run this semantic decision record belongs to. One record per (run, assessment_index).', on_delete=django.db.models.deletion.CASCADE, related_name='semantic_decision_records', to='runs.researchrun')),
            ],
            options={
                'ordering': ['run', 'assessment_index'],
                'indexes': [models.Index(fields=['run', 'assessment_index'], name='sdr_run_assessment_idx')],
                'constraints': [models.UniqueConstraint(fields=('run', 'assessment_index'), name='semantic_decision_record_unique_per_run_assessment'), models.CheckConstraint(condition=models.Q(('schema_version__gte', 1)), name='semantic_decision_record_schema_version_gte_1'), models.CheckConstraint(condition=models.Q(('payload_digest__regex', '^[0-9a-f]{64}$')), name='semantic_decision_record_payload_digest_sha256_hex')],
            },
        ),
    ]
