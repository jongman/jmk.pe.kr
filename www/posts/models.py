# -*- coding: utf-8 -*-
from django.db import models
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.template.loader import get_template
from django.template import Context
from datetime import datetime
from taggit.managers import TaggableManager
from utils import render_text

HIDDEN, NORMAL, STARRED = range(3)
ATTACHMENT_STATE_NAMES = {HIDDEN: u'숨김',
                          NORMAL: u'',
                          STARRED: u'별표'}

PUBLIC, LOGGED_IN, FRIENDS, SIGNIFICANT_OTHER, PRIVATE = range(5)
PERMISSION_NAMES = {PUBLIC: 'Public',
                    LOGGED_IN: 'Only Logged In',
                    FRIENDS: 'Friends',
                    SIGNIFICANT_OTHER: 'Significant Other',
                    PRIVATE: 'Private'}

ALBUM_TYPE = {'full': u'크게 보기',
              'thumbnails': u'썸네일 보기'}

class Redirect(models.Model):
    from_url = models.CharField(max_length=256, db_index=True)
    to_url = models.CharField(max_length=256)
    
class Post(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    dated = models.DateField(u'날짜')
    permission = models.IntegerField(u'공개', choices=PERMISSION_NAMES.items(),
                                    default=PUBLIC)

    slug = models.CharField(u'링크 이름', max_length=100, db_index=True,
                            unique=True)
    title = models.CharField(u'제목', max_length=100)
    album_type = models.CharField(u'앨범 타입', max_length=32,
                                  choices=ALBUM_TYPE.items(),
                                  default='full')

    body_private = models.TextField(u'내용 (비공개)', default='', blank=True)
    body_public = models.TextField(u'내용', default='', blank=True)

    use_excerpts = models.BooleanField(u'축약 사용', default=True)
    pictures = models.ManyToManyField('Attachment', through='AttachedPicture')

    tags = TaggableManager()

    def __unicode__(self):
        return '<Post: %s>' % self.title

    def permission_name(self):
        return PERMISSION_NAMES[self.permission]

    def get_absolute_url(self):
        return reverse('post-read', kwargs={'slug': self.slug})

    def attachments(self):
        return AttachedPicture.objects.filter(post=self).order_by('order').all()

    def clean(self):
        if not self.body_private and not self.body_public:
            raise ValidationError(u"비공개/공개 내용 중 하나는 들어가야 합니다.")


class Attachment(models.Model):
    is_picture = models.BooleanField(default=False, db_index=True)
    date = models.DateField(db_index=True)
    timestamp = models.DateTimeField()
    file = models.FileField()
    thumbnail = models.FileField()
    state = models.IntegerField(default=NORMAL,
                                choices=ATTACHMENT_STATE_NAMES.items())
    original_link = models.CharField(null=True, max_length=256, db_index=True)

    def __unicode__(self):
        return '<Attachment: dated=%s file=%s original_link=%s>' % (
            self.date, self.file, self.original_link)

class AttachedPicture(models.Model):
    post = models.ForeignKey(Post)
    picture = models.ForeignKey(Attachment)

    order = models.IntegerField()
    notes = models.TextField(default='')

    def __unicode__(self):
        return '<AttachedPicture: Post=%s Picture=%s>' % (self.post,
                                                          self.picture)

class Comment(models.Model):
    author = models.ForeignKey(User, null=True)

    name = models.CharField(max_length=100)
    password = models.CharField(max_length=256)
    
    post = models.ForeignKey(Post)
    parent = models.ForeignKey('self', default=None, null=True, related_name='+')
    comment = models.TextField()

    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.IPAddressField(null=True)

    deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return '<Comment: name=%s pk=%d>' % (self.name, self.pk)

