# Generated by Django 3.2.25 on 2025-02-09 08:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accompany', '0005_travelgroup_max_age_travelgroup_min_age'),
    ]

    operations = [
        migrations.AlterField(
            model_name='travelgroup',
            name='gender',
            field=models.CharField(choices=[('전체', '전체'), ('남성만', '남성만'), ('여성만', '여성만')], default='상관없음', max_length=10),
        ),
    ]
