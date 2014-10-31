# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='use_excerpts',
            field=models.BooleanField(default=True, verbose_name='\ud0c0\uc784\ub77c\uc778\uc5d0\ub294 \ucd95\uc57d'),
            preserve_default=True,
        ),
    ]
