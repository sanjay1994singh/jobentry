from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("job_entry", "0009_auto_20260811_1714"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemvalue",
            name="smtp_host",
            field=models.CharField(blank=True, default="smtp.gmail.com", max_length=150),
        ),
        migrations.AddField(
            model_name="systemvalue",
            name="smtp_port",
            field=models.PositiveIntegerField(default=587),
        ),
        migrations.AddField(
            model_name="systemvalue",
            name="smtp_username",
            field=models.CharField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="systemvalue",
            name="smtp_password",
            field=models.CharField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="systemvalue",
            name="smtp_use_tls",
            field=models.BooleanField(default=True),
        ),
    ]
