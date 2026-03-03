from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F


def _backfill_published_flags(apps, schema_editor):
    Submission = apps.get_model("hub", "Submission")
    Submission.objects.filter(
        is_gallery_shared=True,
        is_published=False,
    ).update(
        is_published=True,
        published_at=F("uploaded_at"),
    )


def _noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0023_studentsupporttag"),
    ]

    operations = [
        migrations.AddField(
            model_name="module",
            name="gallery_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="is_published",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="submission",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="process_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="submission",
            name="remix_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="remixes",
                to="hub.submission",
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="station_label",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddIndex(
            model_name="submission",
            index=models.Index(fields=["material", "is_published", "published_at"], name="hub_submis_matpub_f4b5_idx"),
        ),
        migrations.RunPython(_backfill_published_flags, _noop_reverse),
    ]
