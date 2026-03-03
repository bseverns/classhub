from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0022_class_retention_preset"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentSupportTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "tag",
                    models.CharField(
                        choices=[
                            ("needs_extra_time", "Needs extra time"),
                            ("prefers_quiet", "Prefers quiet"),
                            ("device_help", "Device help"),
                        ],
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_support_tags",
                        to="hub.class",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="student_support_tags_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_tags",
                        to="hub.studentidentity",
                    ),
                ),
            ],
            options={
                "ordering": ["student_id", "tag", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="studentsupporttag",
            index=models.Index(fields=["classroom", "tag"], name="hub_stutag_clstag_70a1_idx"),
        ),
        migrations.AddIndex(
            model_name="studentsupporttag",
            index=models.Index(fields=["student", "tag"], name="hub_stutag_sttag_28f8_idx"),
        ),
        migrations.AddConstraint(
            model_name="studentsupporttag",
            constraint=models.UniqueConstraint(
                fields=("classroom", "student", "tag"),
                name="uniq_student_support_tag_per_class",
            ),
        ),
    ]
