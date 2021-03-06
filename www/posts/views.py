# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Group, User
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_user
from django.contrib.auth import logout as logout_user
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template import RequestContext
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.db.models import Min, Max, Count, Q
from django.conf import settings
from uuid import uuid4
import bcrypt
from json import dumps
from taggit.models import Tag
from pytz import timezone
from tempfile import NamedTemporaryFile
from subprocess import check_call
import gc

import json
import hashlib
import os
from cStringIO import StringIO
from models import *
from forms import *
from utils import (setup_paginator, get_client_ip, CalendarPaginator,
                   get_security_question)

from datetime import date, datetime, timedelta
from collections import defaultdict
import calendar as cal

TIMELINE_PPP = 20
SEARCH_PPP = 20 
LIST_PPP = 100
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
    authorized, _ = Group.objects.get_or_create(name='Authorized')
    if authorized in user.groups.all():
        return AUTHORIZED
    friends, _ = Group.objects.get_or_create(name='Friends')
    if friends in user.groups.all():
        return FRIENDS
    so, _ = Group.objects.get_or_create(name='SignificantOther')
    if so in user.groups.all():
        return SIGNIFICANT_OTHER
    return LOGGED_IN

def augment_context(request, ctx):
    perm = determine_permission_level(request.user)
    comments = Comment.objects.filter(deleted=False, post__permission__lte=perm).order_by('-pk')[:20]
    today = date.today()
    past_years = Post.objects.filter(Q(dated__month=today.month),
                                     Q(dated__day=today.day),
                                     permission__lte=perm).order_by('-dated')
    past_years = [post for post in past_years if post.dated != today]
    ctx['recent_comments'] = comments
    ctx['past_years'] = past_years
    ctx['today'] = today
    return ctx

def augmented_render(request, template_name, ctx):
    return render(request, template_name, augment_context(request, ctx))

def gallery(request):
    return augmented_render(request, "gallery.html", {});

def user(request, id):
    comment_user = User.objects.get(id=id)
    perm = determine_permission_level(request.user)
    comments = Comment.objects.filter(author=comment_user, deleted=False, post__permission__lte=perm).order_by('-pk')
    return augmented_render(request, 'user-comments.html', {'comment_user': comment_user, 'comments': comments})

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


def category_first(request, category):
    if category: 
        posts = Post.objects.filter(tags__name__in=[category])
    else:
        posts = Post.objects
    perm = determine_permission_level(request.user)
    posts = posts.filter(permission__lte=perm)
    post = posts.order_by('-timestamp').first()

    return redirect(post.get_absolute_url())


def search(request, page=1):
    perm = determine_permission_level(request.user)
    posts = Post.objects.filter(permission__lte=perm)
    query = request.GET.get('query', u'꺅구라대신')
    criteria = Q(body_public__contains=query) | Q(title__contains=query)
    if perm == PRIVATE:
        criteria = criteria | Q(body_private__contains=query)
    posts = posts.filter(criteria)
    posts = posts.order_by('-timestamp')

    pagination = setup_paginator(posts, SEARCH_PPP, page, 'search', {},
                                 {'query': query}) 
    return augmented_render(request, 'search.html', 
                            {'query': query,
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
    question = get_security_question()
    request.session['expected'] = question['answer']

    post = get_object_or_404(Post, slug=slug)
    if post.permission > determine_permission_level(request.user):
        return HttpResponseForbidden()
    comments = get_comments(post)
    attached = AttachedPicture.objects.filter(post=post).order_by('order').all()
    album_type = album_type or post.album_type

    return augmented_render(request, 'read.html', 
                            {'post': post, 
                             'question': question,
                             'comments': comments, 
                             'album_type': album_type,
                             'comments_count': len(comments)})

@superuser_only
def write_album(request):
    pics = map(int, request.GET.get('pics', '').split(','))
    return write(request, start_with=pics)

jongman_tz = timezone(settings.JONGMAN_TIME_ZONE)
server_tz = timezone(settings.TIME_ZONE)

@superuser_only
def write_journal(request, year='', month='', day=''):
    if not year:
        now = server_tz.localize(datetime.now()).astimezone(jongman_tz)
        dt = now.date()
        if now.hour < 7:
            dt = dt + timedelta(days=-1)
    else:
        dt = date(int(year), int(month), int(day))
    return write(request, date=dt)

@superuser_only
def write(request, id=None, date=None, start_with=None):
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
                    'permission': AUTHORIZED,
                    'album_type': 'full',
                    'tags': 'journal'}

        form = WriteForm(data=data)

    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.save()
        form.save_m2m()

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

    if start_with:
        start_with = [Attachment.objects.get(pk=pk) for pk in start_with]
        start_with = [{'pk': att.pk, 
                       'thumbnail': att.thumbnail.url,
                       'file': att.file.url} for att in start_with]
    else:
        start_with = []

    tags = Tag.objects.all()

    return augmented_render(request, 'write.html', 
                            {'form': form, 'action': action, 'tags': tags,
                             'attachments': attached, 
                             'start_with': dumps(start_with)})


@superuser_only
def delete(request, id):
    post = get_object_or_404(Post, pk=int(id))
    Comment.objects.filter(post=post).delete()
    post.delete()
    clean_empty_tags()
    return redirect('/')


def post_comment(request):
    if not request.user.is_authenticated():
        if (request.POST['security'] != request.session['expected'] or
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
        password = request.POST['password'].encode('utf-8')
        comment.password = bcrypt.hashpw(password, bcrypt.gensalt())

    if request.POST['parent']:
        parent = get_object_or_404(Comment, pk=int(request.POST['parent']))
        comment.parent = parent
    comment.comment = request.POST['body']
    comment.ip_address = get_client_ip(request)
    comment.save()

    return redirect(reverse('post-read', kwargs={'slug': post.slug}))

def check_comment_password(stored, entered):
    entered = entered.encode('utf-8')
    stored = stored.encode('utf-8')
    if stored.startswith('sha1$$'):
        return hashlib.sha1(entered).hexdigest() == stored[6:]
    return bcrypt.hashpw(entered, stored) == stored

def delete_comment(request, id):
    comment = get_object_or_404(Comment, pk=id)
    if comment.author and not (request.user == comment.author or
                               request.user.is_superuser):
        return HttpResponseForbidden()
    if request.method == 'POST':
        if comment.author is None and not request.user.is_superuser:

            if not check_comment_password(comment.password,
                                          request.POST['password']):
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

# shamelessly copied from http://stackoverflow.com/questions/38373877/django-rest-framework-autorotate-image-with-pil
def rotate(image):
    rotated = False
    if hasattr(image, '_getexif'):  # only present in JPEGs
        orientation = None
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        e = image._getexif()  # returns None if no EXIF data
        if e is not None:
            exif = dict(e.items())
            orientation = exif[orientation]

            if orientation == 3:
                rotated = True
                image = image.transpose(Image.ROTATE_180)
            elif orientation == 6:
                rotated = True
                image = image.transpose(Image.ROTATE_270)
            elif orientation == 8:
                rotated = True
                image = image.transpose(Image.ROTATE_90)
    return rotated, image

def image_to_file(filename, image):
    temp = StringIO()
    image.save(temp, 'jpeg')
    temp.seek(0)
    return SimpleUploadedFile(filename, temp.read(), content_type='image/jpeg')

def save_thumbnail(target_path, orig):

    print 'colorspace'
    orig = orig.convert('RGB')
    print 'resizing'
    thumbnail = ImageOps.fit(orig, (THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.ANTIALIAS)
    print 'saving'
    return default_storage.save(target_path, image_to_file('thumbnail.jpg', thumbnail))

@superuser_only
def list_attachment_folders(request):
    pics = Attachment.objects.filter(is_picture=True).exclude(state=HIDDEN)
    annotated = pics.values('date').annotate(first=Min('pk'), cnt=Count('pk'))
    response =  [{'folder': entry['date'].strftime('%Y-%m-%d'),
                  'images': entry['cnt'],
                  'thumbnail': Attachment.objects.get(pk=entry['first']).thumbnail.url}
                 for entry in annotated]
    response.sort(key=lambda e: e['folder'], reverse=True)

    return HttpResponse(json.dumps(response))

@superuser_only
def set_attachment_state(request):
    attachment = get_object_or_404(Attachment, id=int(request.GET.get('pk')))
    state = int(request.GET.get('state'))
    assert state in ATTACHMENT_STATE_NAMES
    attachment.state = state
    attachment.save()
    return HttpResponse('ok')


@superuser_only
def list_attachment(request):
    dt = date(*map(int, request.GET.get('folder').split('-')))

    pics = Attachment.objects.filter(is_picture=True).filter(date=dt).order_by('timestamp')

    response = [{'pk': pic.pk,
                 'thumbnail': pic.thumbnail.url,
                 'state': pic.state,
                 'date': pic.date.strftime('%B %d, %Y').replace(' 0', ' '),
                 'file': pic.file.url}
                for pic in pics]
    return HttpResponse(json.dumps(response))

@superuser_only
def new_attachment(request):
    if request.method != 'POST': return HttpResponseBadRequest()
    def go():
        file = request.FILES.get('file', False)
        print 'processing', file.name
        if not file: return {'success': False,
                             'error': 'file not uploaded',
                             'files': request.FILES.keys()
                            }
        md5 = md5file(file)
        file.seek(0)

        if is_image(file.name):
            with NamedTemporaryFile() as input, NamedTemporaryFile() as output, NamedTemporaryFile() as thumbnail:
                input.write(file.read())
                check_call('/usr/bin/convert -auto-orient {input} {output}'.format(input=input.name, output=output.name).split())
                check_call('/usr/bin/convert {src} -thumbnail {sz}^x{sz}^ -gravity center -extent {sz}x{sz} {thumbnail}'.format(src=output.name, sz=THUMBNAIL_SIZE, thumbnail=thumbnail.name).split())
                file_path = default_storage.save(os.path.join('attachments', md5, file.name), ContentFile(output.read()))
                thumbnail_path = default_storage.save(os.path.join('attachments', md5, 'thumbnail.jpg'), ContentFile(thumbnail.read()))
            is_picture = True
        else:
            file_path = default_storage.save(os.path.join('attachments', md5, file.name), file)
            thumbnail_path = None
            is_picture = False

        thumbnail_path = thumbnail_path or file_path

        dated = date.today()
        now = datetime.now()
        attachment = Attachment(is_picture=is_picture, 
                                date=dated,
                                timestamp=now,
                                file=file_path,
                                thumbnail=thumbnail_path,
                                original_link=None)
        attachment.save()

        return {'success': True, 
                'error': '', 
                'is_picture': attachment.is_picture,
                'file_name': file.name,
                'file_path': attachment.file.url,
                'thumbnail_path': attachment.thumbnail.url,
                'pk': attachment.pk,
               }
    ret = HttpResponse(json.dumps(go()))
    gc.collect()
    return ret

def signup(request):
    security_error = False
    if request.method == 'POST':
        if request.POST['security'] != request.session['expected']:
            security_error = True
        form = SignUpForm(data=request.POST or None)
        if not security_error and form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(username=data['username'],
                                            password=data['password'],
                                            email=data['email'])
            user.is_active = True
            user.save()
            user = authenticate(username=data['username'],
                                password=data['password'])
            login_user(request, user)
            return redirect('/')

    else:
        form = SignUpForm()
    question = get_security_question()
    request.session['expected'] = question['answer']
    return augmented_render(request, 'account/signup.html',
                            {'form': form, 
                             'security_error': security_error,
                             'question': question})

def login(request):
    error = username = u''
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            login_user(request, user)
            return redirect('/')
        else:
            error = u'잘못된 사용자 혹은 비밀번호입니다.'
    return augmented_render(request, 'account/login.html',
                            {'username': username, 'error': error})

def logout(request):
    logout_user(request)
    return redirect('/')

LOST_PW_EMAIL = u'''jmk.pe.kr ID/비밀번호 찾기를 요청하셨습니다.

만일 직접 요청하지 않으셨다면 이 메일을 무시하셔도 좋습니다.

사용자명: %(id)s
비밀번호 찾기 링크: %(recover_url)s

감사합니다.
JM'''

def lost_password(request):
    error = None
    email_sent = False
    if request.method == 'POST':
        email = request.POST['email']
        users = User.objects.filter(email__iexact=email)
        if len(users) == 0:
            error = u'등록되지 않은 이메일입니다.'
        else:
            for user in users:
                uuid = str(uuid4())
                url = reverse('reset-password', kwargs={'uuid': uuid})
                PasswordRecoveryRequest(user=user, uuid=uuid).save()
                send_mail(u'jmk.pe.kr 비밀번호 찾기'.encode('utf-8'),
                          LOST_PW_EMAIL % {'id': user.username,
                                           'recover_url': url},
                          settings.ADMIN_EMAIL,
                          [settings.ADMIN_EMAIL, email])
            email_sent = True

    return augmented_render(request, 'account/lost-password.html',
                            {'email_sent': email_sent, 'error': error})

def reset_password(request, uuid):
    return None

def redirect_legacy_link(request, page):
    r = get_object_or_404(Redirect, from_url='/' + page)
    return redirect(r.to_url)
