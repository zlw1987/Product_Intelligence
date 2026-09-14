# Generated for 7C-A: ComparableResearchExecution model

from django.db import migrations, models
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('runs', '0006_add_ai_assisted_review_candidate'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComparableResearchExecution',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('state', models.CharField(
                    choices=[('PENDING', 'PENDING'), ('RUNNING', 'RUNNING'),
                             ('COMPLETED', 'COMPLETED'), ('FAILED', 'FAILED')],
                    default='PENDING',
                    editable=False,
                    max_length=16,
                )),
                ('active_slot', models.PositiveSmallIntegerField(
                    blank=True,
                    editable=False,
                    help_text='Lifecycle sentinel. 1 when PENDING/RUNNING, NULL when terminal.',
                    null=True,
                )),
                ('created_at', models.DateTimeField(
                    default=django.utils.timezone.now,
                    editable=False,
                )),
                ('started_at', models.DateTimeField(
                    blank=True,
                    editable=False,
                    null=True,
                )),
                ('finished_at', models.DateTimeField(
                    blank=True,
                    editable=False,
                    null=True,
                )),
                ('result_schema_version', models.PositiveSmallIntegerField(
                    blank=True,
                    editable=False,
                    help_text='Codec version of result_payload. NULL until COMPLETED.',
                    null=True,
                )),
                ('result_payload', models.JSONField(
                    blank=True,
                    editable=False,
                    help_text='Versioned codec-encoded ComparableResearchResult. NULL until COMPLETED.',
                    null=True,
                )),
                ('failure_reason', models.CharField(
                    blank=True,
                    editable=False,
                    help_text='Failure reason when state is FAILED. NULL otherwise.',
                    max_length=64,
                    null=True,
                )),
                ('parent_run', models.ForeignKey(
                    on_delete=models.CASCADE,
                    related_name='+',
                    to='runs.researchrun',
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name='comparableresearchexecution',
            constraint=models.CheckConstraint(
                condition=models.Q(active_slot=1) | models.Q(active_slot__isnull=True),
                name='comparable_research_active_slot_is_one_or_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='comparableresearchexecution',
            constraint=models.UniqueConstraint(
                fields=('parent_run', 'active_slot'),
                name='comparable_research_one_active_per_parent',
            ),
        ),
        migrations.AddConstraint(
            model_name='comparableresearchexecution',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    state='PENDING',
                    active_slot=1,
                    started_at__isnull=True,
                    finished_at__isnull=True,
                    result_schema_version__isnull=True,
                    result_payload__isnull=True,
                    failure_reason__isnull=True,
                )
                | models.Q(
                    state='RUNNING',
                    active_slot=1,
                    started_at__isnull=False,
                    finished_at__isnull=True,
                    result_schema_version__isnull=True,
                    result_payload__isnull=True,
                    failure_reason__isnull=True,
                )
                | models.Q(
                    state='COMPLETED',
                    active_slot__isnull=True,
                    started_at__isnull=False,
                    finished_at__isnull=False,
                    result_schema_version__isnull=False,
                    result_schema_version__gte=1,
                    result_payload__isnull=False,
                    failure_reason__isnull=True,
                )
                | models.Q(
                    state='FAILED',
                    active_slot__isnull=True,
                    started_at__isnull=False,
                    finished_at__isnull=False,
                    result_schema_version__isnull=True,
                    result_payload__isnull=True,
                    failure_reason__isnull=False,
                ),
                name='comparable_research_lifecycle_shape',
            ),
        ),
        migrations.AddConstraint(
            model_name='comparableresearchexecution',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('failure_reason__isnull', True),
                    ('failure_reason__in', sorted([
                        'AUTHORITY_FETCH_FAILED', 'AUTHORITY_SOURCE_REFUSED',
                        'AUTHORITY_HOST_ESCAPED', 'AUTHORITY_NO_STRUCTURAL_OBSERVATIONS',
                        'SPECIFICATION_EXTRACTION_FAILED', 'DISCOVERY_FAILED',
                        'COMPOSITION_FAILED', 'SCORING_FAILED',
                        'RESULT_ENCODING_FAILED', 'INTERNAL_ERROR',
                    ])),
                    _connector='OR',
                ),
                name='comparable_research_valid_failure_reason',
            ),
        ),
        migrations.AddIndex(
            model_name='comparableresearchexecution',
            index=models.Index(
                fields=('parent_run', 'state'),
                name='runs_compar_parent__64567d_idx',
            ),
        ),
    ]
