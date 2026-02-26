from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import hub.models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0011_submission_uploaded_at_indexes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassInviteLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(default=hub.models.gen_student_invite_token, max_length=48, unique=True)),
                ("label", models.CharField(blank=True, default="", max_length=120)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("max_uses", models.PositiveIntegerField(blank=True, null=True)),
                ("use_count", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "classroom",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invite_links", to="hub.class"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="class_invites_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="classinvitelink",
            index=models.Index(fields=["classroom", "is_active"], name="hub_clsinv_clsact_93d2_idx"),
        ),
        migrations.AddIndex(
            model_name="classinvitelink",
            index=models.Index(fields=["classroom", "created_at"], name="hub_clsinv_clscrt_5d9a_idx"),
        ),
        migrations.AddIndex(
            model_name="classinvitelink",
            index=models.Index(fields=["expires_at"], name="hub_clsinv_exp_a2e1_idx"),
        ),
    ]
