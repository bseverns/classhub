from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0021_class_student_landing_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="class",
            name="retention_preset",
            field=models.CharField(
                choices=[
                    ("erase_after_7_days", "Erase after 7 days"),
                    ("keep_for_semester", "Keep for semester"),
                    ("keep_until_student_deletes", "Keep portfolio until student deletes"),
                ],
                default="erase_after_7_days",
                max_length=40,
            ),
        ),
    ]
