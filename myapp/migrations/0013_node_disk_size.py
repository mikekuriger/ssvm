# Generated by Django 3.2.25 on 2024-10-16 22:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0012_deployment_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='disk_size',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
