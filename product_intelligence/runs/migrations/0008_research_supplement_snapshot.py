"""Auto-generated migration for ResearchSupplementSnapshot (4D-B)."""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("runs", "0007_comparable_research_execution"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResearchSupplementSnapshot",
            fields=[
                (
                    "run",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        related_name="research_supplement_snapshot",
                        to="runs.researchrun",
                        help_text="The research run this supplemental snapshot belongs to.",
                    ),
                ),
                (
                    "schema_version",
                    models.PositiveSmallIntegerField(
                        help_text=(
                            "Codec version that produced the payload. "
                            "Initial supported value is 1."
                        )
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        help_text="Versioned codec-encoded supplemental result."
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
        ),
        migrations.AddConstraint(
            model_name="researchsupplementsnapshot",
            constraint=models.CheckConstraint(
                check=models.Q(("schema_version__gte", 1)),
                name="research_supplement_snapshot_schema_version_gte_1",
            ),
        ),
    ]
