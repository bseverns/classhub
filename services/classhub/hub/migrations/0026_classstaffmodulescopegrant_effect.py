from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0025_classstaffmodulescopegrant"),
    ]

    operations = [
        migrations.AddField(
            model_name="classstaffmodulescopegrant",
            name="effect",
            field=models.CharField(
                choices=[("allow", "Allow"), ("deny", "Deny")],
                default="allow",
                max_length=16,
            ),
        ),
        migrations.RemoveIndex(
            model_name="classstaffmodulescopegrant",
            name="hub_stmodgr_clsusr_cap_idx",
        ),
        migrations.RemoveIndex(
            model_name="classstaffmodulescopegrant",
            name="hub_stmodgr_scope_rng_idx",
        ),
        migrations.AddIndex(
            model_name="classstaffmodulescopegrant",
            index=models.Index(
                fields=["classroom", "user", "capability", "effect", "is_active"],
                name="hub_stmodgr_clsusr_cap_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="classstaffmodulescopegrant",
            index=models.Index(
                fields=["classroom", "capability", "effect", "module_order_start", "module_order_end"],
                name="hub_stmodgr_scope_rng_idx",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="classstaffmodulescopegrant",
            name="uniq_staff_module_scope_grant",
        ),
        migrations.AddConstraint(
            model_name="classstaffmodulescopegrant",
            constraint=models.UniqueConstraint(
                fields=("classroom", "user", "capability", "effect", "module_order_start", "module_order_end"),
                name="uniq_staff_module_scope_effect_grant",
            ),
        ),
    ]
