# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AttachedPicture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.IntegerField()),
                ('notes', models.TextField(default=b'')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_picture', models.BooleanField(default=False, db_index=True)),
                ('date', models.DateField(db_index=True)),
                ('timestamp', models.DateTimeField()),
                ('file', models.FileField(upload_to=b'')),
                ('thumbnail', models.FileField(upload_to=b'')),
                ('state', models.IntegerField(default=1, choices=[(0, '\uc228\uae40'), (1, ''), (2, '\ubcc4\ud45c')])),
                ('original_link', models.CharField(max_length=256, null=True, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('password', models.CharField(max_length=256)),
                ('comment', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.IPAddressField(null=True)),
                ('deleted', models.BooleanField(default=False)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
                ('parent', models.ForeignKey(related_name=b'+', default=None, to='posts.Comment', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('dated', models.DateField(verbose_name='\ub0a0\uc9dc')),
                ('permission', models.IntegerField(default=0, verbose_name='\uacf5\uac1c', choices=[(0, b'Public'), (1, b'Only Logged In'), (2, b'Friends'), (3, b'Significant Other'), (4, b'Private')])),
                ('slug', models.CharField(unique=True, max_length=100, verbose_name='\ub9c1\ud06c \uc774\ub984', db_index=True)),
                ('title', models.CharField(max_length=100, verbose_name='\uc81c\ubaa9')),
                ('album_type', models.CharField(default=b'full', max_length=32, verbose_name='\uc568\ubc94 \ud0c0\uc785', choices=[(b'full', '\ud06c\uac8c \ubcf4\uae30'), (b'thumbnails', '\uc378\ub124\uc77c \ubcf4\uae30')])),
                ('body_private', models.TextField(default=b'', verbose_name='\ub0b4\uc6a9 (\ube44\uacf5\uac1c)', blank=True)),
                ('body_public', models.TextField(default=b'', verbose_name='\ub0b4\uc6a9', blank=True)),
                ('pictures', models.ManyToManyField(to='posts.Attachment', through='posts.AttachedPicture')),
                ('tags', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Redirect',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('from_url', models.CharField(max_length=256, db_index=True)),
                ('to_url', models.CharField(max_length=256)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='comment',
            name='post',
            field=models.ForeignKey(to='posts.Post'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='attachedpicture',
            name='picture',
            field=models.ForeignKey(to='posts.Attachment'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='attachedpicture',
            name='post',
            field=models.ForeignKey(to='posts.Post'),
            preserve_default=True,
        ),
    ]
