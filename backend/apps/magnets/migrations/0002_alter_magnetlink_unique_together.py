# Generated by Django 4.2.7 on 2025-07-20 09:09

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("magnets", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="magnetlink",
            unique_together=set(),
        ),
    ]
