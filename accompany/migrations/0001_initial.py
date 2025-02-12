# Generated by Django 3.2.25 on 2025-02-13 01:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Accompany_Zzim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='AccompanyRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='TravelGroup',
            fields=[
                ('travel_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=100)),
                ('city', models.CharField(max_length=50)),
                ('explanation', models.TextField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('now_member', models.IntegerField(default=1)),
                ('max_member', models.IntegerField()),
                ('tags', models.TextField(blank=True, null=True)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='static/travel_photos/')),
                ('gender', models.CharField(choices=[('전체', '전체'), ('남성만', '남성만'), ('여성만', '여성만')], default='상관없음', max_length=10)),
                ('min_age', models.IntegerField(blank=True, null=True)),
                ('max_age', models.IntegerField(blank=True, null=True)),
                ('markers', models.JSONField(blank=True, null=True)),
                ('polyline', models.JSONField(blank=True, null=True)),
                ('this_plan_id', models.IntegerField(blank=True, null=True)),
                ('call_schedule', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TravelParticipants',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('travel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='travel_participants', to='accompany.travelgroup')),
            ],
        ),
    ]
