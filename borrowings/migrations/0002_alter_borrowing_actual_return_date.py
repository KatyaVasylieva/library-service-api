# Generated by Django 4.1.7 on 2023-03-23 12:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("borrowings", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="borrowing",
            name="actual_return_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
