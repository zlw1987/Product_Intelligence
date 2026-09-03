# Generated for HUMAN-REVIEW: AiAssistedReviewCandidate model

from django.db import migrations, models
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0005_alter_executionevidencerecord_stage'),
    ]

    operations = [
        migrations.CreateModel(
            name='AiAssistedReviewCandidate',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    help_text='Candidate UUID. Used as the browser POST action identifier.',
                    primary_key=True,
                    serialize=False,
                )),
                ('assessment_index', models.PositiveSmallIntegerField(
                    help_text='Position of the corresponding ListingIdentityAssessment '
                    'in the ordered assessments tuple of PriceIntelligenceSnapshot.',
                )),
                ('source_url', models.TextField(
                    help_text='The listing source URL. Stored exactly as observed.',
                )),
                ('target_mpn', models.TextField(
                    editable=False,
                    help_text='The request MPN, from the semantic result.',
                )),
                ('target_description', models.TextField(
                    blank=True,
                    editable=False,
                    help_text='The request description, from the semantic result.',
                )),
                ('candidate_title', models.TextField(
                    editable=False,
                    help_text='The listing product title, from the semantic result.',
                )),
                ('candidate_mpn_field', models.TextField(
                    blank=True,
                    editable=False,
                    help_text='The raw MPN field from the listing.',
                )),
                ('candidate_sku', models.TextField(
                    blank=True,
                    editable=False,
                    help_text='The SKU field from the listing, if available.',
                )),
                ('candidate_specs', models.TextField(
                    blank=True,
                    editable=False,
                    help_text='Concatenated listing specs (brand/MPN/SKU/condition).',
                )),
                ('evidence_source', models.CharField(
                    editable=False,
                    help_text='Evidence source vocabulary (TITLE_TEXT, SKU_FIELD, etc.).',
                    max_length=32,
                )),
                ('semantic_confidence', models.CharField(
                    blank=True,
                    editable=False,
                    help_text='Semantic confidence level (LOW, MEDIUM, etc.).',
                    max_length=16,
                )),
                ('semantic_reason_code', models.TextField(
                    blank=True,
                    editable=False,
                    help_text='Semantic reason code explaining the MATCH.',
                )),
                ('semantic_matched_attributes', models.JSONField(
                    default=list,
                    editable=False,
                    help_text='JSON array of matched attribute names.',
                )),
                ('semantic_conflicting_attributes', models.JSONField(
                    default=list,
                    editable=False,
                    help_text='JSON array of conflicting attribute names.',
                )),
                ('actual_provider', models.CharField(
                    editable=False,
                    help_text='Provider that produced the semantic response.',
                    max_length=64,
                )),
                ('actual_model', models.CharField(
                    editable=False,
                    help_text='Model that produced the semantic response.',
                    max_length=128,
                )),
                ('prompt_version', models.CharField(
                    editable=False,
                    help_text='Semantic prompt version used.',
                    max_length=16,
                )),
                ('review_state', models.CharField(
                    choices=[('UNREVIEWED', 'UNREVIEWED'), ('CONFIRMED', 'CONFIRMED'), ('REJECTED', 'REJECTED')],
                    default='UNREVIEWED',
                    help_text='Current review state: UNREVIEWED, CONFIRMED, or REJECTED.',
                    max_length=16,
                )),
                ('created_at', models.DateTimeField(
                    default=django.utils.timezone.now,
                    editable=False,
                    help_text='When this candidate record was persisted.',
                )),
                ('reviewed_at', models.DateTimeField(
                    blank=True,
                    editable=False,
                    help_text='When the review state was last changed. Null for UNREVIEWED.',
                    null=True,
                )),
                ('run', models.ForeignKey(
                    help_text='The research run this candidate belongs to.',
                    on_delete=models.CASCADE,
                    related_name='ai_assisted_review_candidates',
                    to='runs.researchrun',
                )),
            ],
            options={
                'ordering': ['run', 'assessment_index'],
            },
        ),
        migrations.AddConstraint(
            model_name='aiassistedreviewcandidate',
            constraint=models.UniqueConstraint(
                fields=('run', 'assessment_index'),
                name='ai_assisted_review_unique_candidate_per_run_assessment',
            ),
        ),
        migrations.AddIndex(
            model_name='aiassistedreviewcandidate',
            index=models.Index(
                fields=('run', 'review_state'),
                name='runs_aiassi_run_id_0de54e_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='aiassistedreviewcandidate',
            constraint=models.CheckConstraint(
                check=models.Q(reviewed_at__isnull=True, review_state='UNREVIEWED')
                | models.Q(reviewed_at__isnull=False, review_state__in=['CONFIRMED', 'REJECTED']),
                name='ai_assisted_review_state_timestamp_consistency',
                violation_error_message='UNREVIEWED requires reviewed_at NULL; CONFIRMED/REJECTED requires reviewed_at NOT NULL.',
            ),
        ),
    ]
