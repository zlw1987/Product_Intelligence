# Generated migration for ResearchMicronAliasSnapshot (PRODUCT-INTEL.4D-D)

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("runs", "0009_research_fx_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResearchMicronAliasSnapshot",
            fields=[
                (
                    "run",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        related_name="research_micron_alias_snapshot",
                        to="runs.researchrun",
                        help_text="The research run this alias snapshot belongs to.",
                    ),
                ),
                (
                    "schema_version",
                    models.PositiveSmallIntegerField(
                        help_text="Codec version that produced the payload. Initial supported value is 1."
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        help_text="Versioned codec-encoded bounded alias-authority audit."
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="When this snapshot record was persisted.",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        check=models.Q(("schema_version__gte", 1)),
                        name="research_micron_alias_snapshot_schema_version_gte_1",
                    ),
                ],
            },
        ),
    ]
