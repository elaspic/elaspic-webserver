# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-16 22:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web_pipeline', '0003_coremutationlocal_elaspic_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='interfacemutationlocal',
            name='elaspic_version',
            field=models.CharField(max_length=255, null=True),
        ),
    ]