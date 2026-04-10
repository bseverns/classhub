from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RemoteComputeClassMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("class_id", models.PositiveIntegerField(unique=True)),
                ("activation_count", models.PositiveIntegerField(default=0)),
                ("ready_transition_count", models.PositiveIntegerField(default=0)),
                ("cumulative_ready_seconds", models.PositiveIntegerField(default=0)),
                ("remote_route_count", models.PositiveIntegerField(default=0)),
                ("fallback_local_count", models.PositiveIntegerField(default=0)),
                ("degraded_transition_count", models.PositiveIntegerField(default=0)),
                ("provider_unreachable_count", models.PositiveIntegerField(default=0)),
                ("unused_activation_count", models.PositiveIntegerField(default=0)),
                ("last_activation_at", models.DateTimeField(blank=True, null=True)),
                ("last_ready_at", models.DateTimeField(blank=True, null=True)),
                ("last_fallback_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="RemoteComputeLeaseRecord",
            fields=[
                ("slot", models.CharField(default="active", editable=False, max_length=32, primary_key=True, serialize=False)),
                ("state", models.CharField(default="off", max_length=32)),
                ("class_id", models.PositiveIntegerField(default=0)),
                ("requested_by", models.CharField(blank=True, max_length=150)),
                ("requested_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("provider_request_id", models.CharField(blank=True, max_length=120)),
                ("status_detail", models.CharField(blank=True, max_length=160)),
                ("last_error_code", models.CharField(blank=True, max_length=80)),
                ("last_transition_at", models.DateTimeField(blank=True, null=True)),
                ("last_healthcheck_at", models.DateTimeField(blank=True, null=True)),
                ("last_routed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

