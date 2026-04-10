from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("tutor", "0001_remote_compute_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="remotecomputeleaserecord",
            name="last_readiness_reason_code",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="remotecomputeleaserecord",
            name="last_ready_probe_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="remotecomputeleaserecord",
            name="last_ready_probe_ok_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="remotecomputeleaserecord",
            name="lease_session_id",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="remotecomputeleaserecord",
            name="requested_duration_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="RemoteComputeLeaseSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("class_id", models.PositiveIntegerField(db_index=True)),
                ("requested_by", models.CharField(blank=True, max_length=150)),
                ("requested_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("requested_duration_minutes", models.PositiveIntegerField(default=0)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("provider_label", models.CharField(blank=True, max_length=80)),
                ("provider_adapter", models.CharField(blank=True, max_length=80)),
                ("provider_request_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("current_state", models.CharField(db_index=True, default="requested", max_length=32)),
                ("last_transition_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_healthcheck_at", models.DateTimeField(blank=True, null=True)),
                ("last_ready_probe_at", models.DateTimeField(blank=True, null=True)),
                ("last_ready_probe_ok_at", models.DateTimeField(blank=True, null=True)),
                ("first_ready_at", models.DateTimeField(blank=True, null=True)),
                ("last_routed_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_code", models.CharField(blank=True, max_length=80)),
                ("last_readiness_reason_code", models.CharField(blank=True, max_length=80)),
                ("last_fallback_reason_code", models.CharField(blank=True, max_length=80)),
                ("status_detail", models.CharField(blank=True, max_length=160)),
                ("starting_seconds", models.PositiveIntegerField(default=0)),
                ("ready_seconds", models.PositiveIntegerField(default=0)),
                ("degraded_seconds", models.PositiveIntegerField(default=0)),
                ("leased_minutes", models.PositiveIntegerField(default=0)),
                ("manual_stop_count", models.PositiveIntegerField(default=0)),
                ("auto_stop_count", models.PositiveIntegerField(default=0)),
                ("remote_route_count", models.PositiveIntegerField(default=0)),
                ("fallback_local_count", models.PositiveIntegerField(default=0)),
                (
                    "estimated_cost_per_hour_usd",
                    models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=8, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-requested_at", "-id")},
        ),
        migrations.CreateModel(
            name="RemoteComputeLeaseEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("event_type", models.CharField(max_length=48)),
                ("from_state", models.CharField(blank=True, max_length=32)),
                ("to_state", models.CharField(blank=True, max_length=32)),
                ("reason_code", models.CharField(blank=True, max_length=80)),
                ("detail", models.CharField(blank=True, max_length=160)),
                (
                    "lease_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="tutor.remotecomputeleasesession",
                    ),
                ),
            ],
            options={"ordering": ("-occurred_at", "-id")},
        ),
    ]
