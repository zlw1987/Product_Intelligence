# Generated migration for ResearchFxSnapshot (PRODUCT-INTEL.4D-C-A)

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("runs", "0008_research_supplement_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResearchFxSnapshot",
            fields=[
                (
                    "run",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        related_name="research_fx_snapshot",
                        to="runs.researchrun",
                        help_text="The research run this FX snapshot belongs to.",
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
                        help_text="Versioned codec-encoded FX observation."
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
                        name="research_fx_snapshot_schema_version_gte_1",
                    ),
                ],
            },
        ),
    ]
