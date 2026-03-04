from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0024_module_gallery_and_submission_artifact_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassStaffModuleScopeGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "capability",
                    models.CharField(
                        choices=[
                            ("submission.view", "Submission view"),
                            ("submission.delete", "Submission delete"),
                        ],
                        max_length=40,
                    ),
                ),
                ("module_order_start", models.PositiveIntegerField(default=0)),
                ("module_order_end", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_module_scope_grants",
                        to="hub.class",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="classhub_module_scope_grants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "classroom_id",
                    "user_id",
                    "capability",
                    "module_order_start",
                    "module_order_end",
                    "id",
                ],
            },
        ),
        migrations.AddIndex(
            model_name="classstaffmodulescopegrant",
            index=models.Index(
                fields=["classroom", "user", "capability", "is_active"],
                name="hub_stmodgr_clsusr_cap_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="classstaffmodulescopegrant",
            index=models.Index(
                fields=["classroom", "capability", "module_order_start", "module_order_end"],
                name="hub_stmodgr_scope_rng_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="classstaffmodulescopegrant",
            constraint=models.UniqueConstraint(
                fields=("classroom", "user", "capability", "module_order_start", "module_order_end"),
                name="uniq_staff_module_scope_grant",
            ),
        ),
        migrations.AddConstraint(
            model_name="classstaffmodulescopegrant",
            constraint=models.CheckConstraint(
                check=models.Q(module_order_end__gte=models.F("module_order_start")),
                name="staff_module_scope_order_valid",
            ),
        ),
    ]
