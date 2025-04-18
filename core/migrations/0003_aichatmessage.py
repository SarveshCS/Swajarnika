# Generated by Django 5.2 on 2025-04-04 21:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_patient_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('is_ai', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.patient')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
