# Generated by Django 4.1.7 on 2023-04-13 10:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("borrowings", "0005_alter_payment_session_id_alter_payment_session_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="session_id",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name="payment",
            name="session_url",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
