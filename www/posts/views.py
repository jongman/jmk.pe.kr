# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group, User
from django.core.files.storage import DefaultStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import RequestContext
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.db.models import Min, Max
import bcrypt
from taggit.models import Tag
from PIL import Image, ImageOps

import json
import hashlib
import os
from cStringIO import StringIO
from models import *
from forms import *
from utils import setup_paginator, get_client_ip, CalendarPaginator

from datetime import date, datetime, timedelta
from collections import defaultdict
import calendar as cal

TIMELINE_PPP = 30
LIST_PPP = 500
THUMBNAIL_SIZE = 150

def clean_empty_tags():
    # clean empty tags
    for tag in Tag.objects.all():
        if tag.taggit_taggeditem_items.count() == 0:
            tag.delete()

def superuser_only(decorated):
    def func(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        return decorated(request, *args, **kwargs)
    return func

def determine_permission_level(user):
    if not user.is_authenticated():
        return PUBLIC
    if user.is_superuser:
        return PRIVATE
    friends, _ = Group.objects.get_or_create(name='Friends')
    if friends in user.groups:
        return FRIENDS
    return LOGGED_IN

def augment_context(request, ctx):
    perm = determine_permission_level(request.user)
    comments = Comment.objects.filter(deleted=False, post__permission__lte=perm).order_by('-pk')[:20]
    ctx['recent_comments'] = comments
    return ctx

def augmented_render(request, template_name, ctx):
    return render(request, template_name, augment_context(request, ctx))

def timeline(request, category='', page=1):
    if category: 
        posts = Post.objects.filter(tags__name__in=[category])
    else:
        posts = Post.objects
    perm = determine_permission_level(request.user)
    posts = posts.filter(permission__lte=perm)
    posts = posts.order_by('-timestamp')

    kwargs = {'category': category} if category else {}
    pagination = setup_paginator(posts, TIMELINE_PPP, page, 'timeline', kwargs) 

    return augmented_render(request, 'timeline.html', 
                            {'category': category,
                             'pagination': pagination})

def calendar(request, category='', year='', month=''):
    if not year:
        today = date.today()
        year, month = today.year, today.month
    else:
        year, month = map(int, (year, month))

    if category: 
        posts = Post.objects.filter(tags__name__in=[category])
    else:
        posts = Post.objects

    perm = determine_permission_level(request.user)
    posts = posts.filter(permission__lte=perm)

    first_date = posts.aggregate(Min('dated'))['dated__min']
    last_date = posts.aggregate(Max('dated'))['dated__max']
    if first_date is None:
        first_date = last_date = date.today()

    kwargs = {'category': category} if category else {}
    paginator = CalendarPaginator(first_date, last_date, year, month,
                                  'calendar', kwargs)

    posts = posts.filter(dated__year=year, dated__month=month)
    posts = posts.order_by('-timestamp')
    by_date = defaultdict(list)
    for post in posts:
        by_date[post.dated.day].append(post)

    augmented_calendar = []

   
    for week in cal.Calendar(firstweekday=6).monthdays2calendar(year, month):
        augmented_week = []
        for day, dow in week:
            augmented_week.append((day, dow, by_date[day]))
        augmented_calendar.append(augmented_week)

    return augmented_render(request, 'calendar.html', 
                            {'category': category, 
                             'year': year,
                             'month': month,
                             'calendar': augmented_calendar,
                             'pagination': paginator})

def list_posts(request, category='', page=1):
    if category: 
        posts = Post.objects.filter(tags__name__in=[category])
    else:
        posts = Post.objects
    perm = determine_permission_level(request.user)
    posts = posts.filter(permission__lte=perm)
    posts = posts.order_by('-timestamp')
    kwargs = {'category': category} if category else {}
    pagination = setup_paginator(posts, LIST_PPP, page, 'list', kwargs) 

    return augmented_render(request, 'list.html', 
                            {'category': category,
                             'pagination': pagination})



def categories(request):
    perm = determine_permission_level(request.user)

    samples = []
    for tag in Tag.objects.order_by('name'):
        posts = Post.objects.filter(tags__name__in=[tag.name],
                                    permission__lte=perm)
        cnt = posts.count()
        if cnt == 0: continue
        posts = posts.order_by('-timestamp')
        posts = posts[:3]
        samples.append((tag, cnt, posts))
    return augmented_render(request, 'categories.html', 
                            {'categories': samples})

def get_comments(post):
    tree = {}
    for comment in Comment.objects.filter(post=post).order_by('pk'):
        tree.setdefault(comment.parent, []).append(comment)

    comments = []
    def dfs(root, depth):
        if root:
            comments.append((depth, root))
        for children in tree.get(root, []):
            dfs(children, depth+1)

    dfs(None, -1)
    return comments

def read(request, slug, album_type=''):
    post = get_object_or_404(Post, slug=slug)
    if post.permission > determine_permission_level(request.user):
        return HttpResponseForbidden()
    comments = get_comments(post)
    attached = AttachedPicture.objects.filter(post=post).order_by('order').all()
    album_type = album_type or post.album_type

    return augmented_render(request, 'read.html', 
                            {'post': post, 
                             'attachments': attached,
                             'comments': comments, 
                             'album_type': album_type,
                             'comments_count': len(comments)})

@superuser_only
def write_journal(request, year='', month='', day=''):
    if not year:
        dt = date.today()
        if datetime.now().hour < 7:
            dt = dt + timedelta(days=-1)
    else:
        dt = date(int(year), int(month), int(day))
    return write(request, date=dt)

@superuser_only
def write(request, id=None, date=None):
    action = u'New Post'
    attachments = []
    if id:
        post = get_object_or_404(Post, pk=int(id))
        form = WriteForm(data=request.POST or None, instance=post)
        action = u'Edit Post'
    else:
        data = None
        if request.method == 'POST':
            data = request.POST
        elif date is not None:
            data = {'title': date.strftime('%Y%m%d'),
                    'slug': date.strftime('%Y%m%d'),
                    'dated': date.strftime('%Y-%m-%d'),
                    'permission': PUBLIC,
                    'album_type': 'full',
                    'tags': 'journal'}

        form = WriteForm(data=data)

    if request.method == 'POST' and form.is_valid():
        post = form.save()

        att = json.loads(request.POST['serialized_attachments'])
        post.pictures.clear()
        for order, attachment in enumerate(att):
            picture = Attachment.objects.get(pk=int(attachment['pk']))
            AttachedPicture(picture=picture, post=post, order=order,
                            notes=attachment['notes']).save()

        clean_empty_tags()
        return redirect(reverse('post-read', kwargs={'slug': post.slug})) 

    if request.method == 'POST':
        attached = json.loads(request.POST['serialized_attachments'])
    elif id:
        attached = AttachedPicture.objects.filter(post=post).order_by('order')
        attached = [{'pk': att.picture.pk, 
                     'thumbnail': att.picture.thumbnail.url,
                     'file': att.picture.file.url,
                     'notes': att.notes} for att in attached]
    else:
        attached = []

    tags = Tag.objects.all()

    return augmented_render(request, 'write.html', 
                            {'form': form, 'action': action, 'tags': tags,
                             'attachments': attached})


@superuser_only
def delete(request, id):
    post = get_object_or_404(Post, pk=int(id))
    Comment.objects.filter(post=post).delete()
    post.delete()
    clean_empty_tags()
    return redirect('/')


def post_comment(request):
    if not request.user.is_authenticated():
        if (request.POST['question'] != u'삼천리' or
            not request.POST['name'] or 
            not request.POST['password']):
            return HttpResponseForbidden()
    if not request.POST['body'] or not request.POST['post']:
        return HttpResponseForbidden()

    post = get_object_or_404(Post, pk=int(request.POST['post']))
    comment = Comment(post=post)

    if request.user.is_authenticated():
        comment.author = request.user
        comment.name = request.user.username
    else:
        comment.name = request.POST['name']
        comment.password = bcrypt.hashpw(request.POST['password'], 
                                         bcrypt.gensalt())

    if request.POST['parent']:
        parent = get_object_or_404(Comment, pk=int(request.POST['parent']))
        comment.parent = parent
    comment.comment = request.POST['body']
    comment.ip_address = get_client_ip(request)
    comment.save()

    return redirect(reverse('post-read', kwargs={'slug': post.slug}))

def delete_comment(request, id):
    comment = get_object_or_404(Comment, pk=id)
    if comment.author and not (request.user == comment.author or
                               request.user.is_superuser):
        return HttpResponseForbidden()
    if request.method == 'POST':
        if comment.author is None and not request.user.is_superuser:
            if not bcrypt.checkpw(request.POST['password'], comment.password):
                return augmented_render(request, 'delete-comment.html', 
                                        {'comment': comment, 
                                         'error': u'비밀번호가 틀립니다.'})
        comment.deleted = True
        post = comment.post
        comment.save()
        return redirect(reverse('post-read', kwargs={'slug': post.slug}))

    return augmented_render(request, 'delete-comment.html', {'comment': comment})

def album_view(request):
    pass

def blog_view(request):
    pass

def all_comments(request):
    pass

def md5file(file):
    md5 = hashlib.md5()
    for chunk in file.chunks():
        md5.update(chunk)
    return md5.hexdigest()

def is_image(file_name):
    return file_name.lower().split('.')[-1] in ('jpeg', 'jpg', 'png', 'gif')

def save_thumbnail(target_path, file):
    orig = Image.open(StringIO(file.read()))
    thumbnail = ImageOps.fit(orig, (THUMBNAIL_SIZE, THUMBNAIL_SIZE),
                             Image.ANTIALIAS)
    temp = StringIO()
    thumbnail.save(temp, 'jpeg')
    temp.seek(0)

    suf = SimpleUploadedFile(file.name, temp.read(), content_type='image/jpeg')
    storage = DefaultStorage()
    return storage.save(target_path, suf)

@superuser_only
def list_attachment_folders(request):
    pics = Attachment.objects.filter(is_picture=True)
    folders = pics.values('folder').distinct().order_by('-folder')
    return HttpResponse(json.dumps([f['folder'] for f in folders]))

@superuser_only
def list_attachment(request):
    folder = request.GET.get('folder')
    pics = Attachment.objects.filter(is_picture=True)
    pics = pics.filter(folder=folder).order_by('pk')
    response = [{'pk': pic.pk,
                 'thumbnail': pic.thumbnail.url,
                 'starred': pic.starred,
                 'file': pic.file.url}
                for pic in pics]
    return HttpResponse(json.dumps(response))

@superuser_only
def new_attachment(request):
    if request.method != 'POST': return HttpResponseBadRequest()
    def go():
        file = request.FILES.get('file', False)
        if not file: return {'success': False,
                             'error': 'file not uploaded',
                             'files': request.FILES.keys()
                            }
        md5 = md5file(file)
        target_path = os.path.join('attachments', md5, file.name)
        storage = DefaultStorage()
        file_path = storage.save(target_path, file)

        is_picture = False
        if is_image(file.name):
            target_path = os.path.join('attachments', md5, 'thumbnail.jpg')
            file.seek(0)
            thumbnail_path = save_thumbnail(target_path, file)
            is_picture = True
        else:
            thumbnail_path = file_path

        folder = date.today().strftime('%Y-%m') + '-uploaded'
        attachment = Attachment(is_picture=is_picture, 
                                folder=folder,
                                file=file_path,
                                thumbnail=thumbnail_path,
                                starred=False,
                                original_link=None)
        attachment.save()

        return {'success': True, 
                'error': '', 
                'is_picture': attachment.is_picture,
                'file_path': attachment.file.url,
                'thumbnail_path': attachment.thumbnail.url,
                'pk': attachment.pk,
               }
    return HttpResponse(json.dumps(go()))

