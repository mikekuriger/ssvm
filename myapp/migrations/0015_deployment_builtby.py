# Generated by Django 3.2.25 on 2024-10-17 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0014_auto_20241016_2311'),
    ]

    operations = [
        migrations.AddField(
            model_name='deployment',
            name='builtby',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
