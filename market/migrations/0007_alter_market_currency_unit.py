# Generated by Django 5.1.5 on 2025-02-08 20:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0006_market_currency_unit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="market",
            name="currency_unit",
            field=models.CharField(
                choices=[("₩", "원"), ("$", "달러"), ("€", "유로")], max_length=10
            ),
        ),
    ]
