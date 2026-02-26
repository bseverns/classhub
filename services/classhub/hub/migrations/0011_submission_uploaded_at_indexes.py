from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0010_lessonrelease_helper_tuning"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="submission",
            index=models.Index(
                fields=["material", "uploaded_at"],
                name="hub_submis_matup_2a3bf4_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="submission",
            index=models.Index(
                fields=["student", "uploaded_at"],
                name="hub_submiss_student_4f0ac8_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="submission",
            index=models.Index(
                fields=["material", "student"],
                name="hub_submis_matstu_91b9f2_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="studentidentity",
            index=models.Index(
                fields=["classroom", "created_at"],
                name="hub_studid_clscrt_a1d2_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="studentevent",
            index=models.Index(
                fields=["classroom", "event_type", "created_at"],
                name="hub_ste_cl_evtcr_b2e3_idx",
            ),
        ),
    ]
