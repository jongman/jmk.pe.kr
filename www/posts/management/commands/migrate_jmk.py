# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.core.files.storage import DefaultStorage
from optparse import make_option
from posts.models import *
from posts.views import save_thumbnail
from os import path, makedirs
from shutil import copyfile
import hashlib
import re
import MySQLdb
import MySQLdb.cursors

PERMISSION_MAP = {0: PRIVATE,
                  1: SIGNIFICANT_OTHER,
                  5: FRIENDS,
                  9: PUBLIC,
                  10: PUBLIC}
TAGS_MAP = {
    '/': ['to-sort'],
    'after': ['impressions'],
    'guestbook': ['guestbooks'],
    '/after/books/': ['impressions'],
    'conferences': ['travel'],
    'dance': ['impressions'],
    'games': ['impressions'],
    'movies': ['impressions'],
    'music': ['links'],
    'talks': ['talks'],
    '/archive/books/': ['archive'],
    '/archive/courses/': ['archive'],
    'archive': ['archive'],
    'intro': ['about'],
    'journal': ['journal'],
    'contest': ['ps'],
    'dev': ['journal'],
    '/journal/logs/': ['journal'],
    'marriage': ['journal'],
    'money': ['personalfinance'],
    '/journal/travel/': ['albums', 'travel'],
    'contests': ['ps'],
    'postmortem': ['ps'],
    'financial': ['personalfinance'],
    'library': ['ps'],
    'reviews': ['journal'],
    'spoj': ['ps'],
    'topcoder': ['ps'],
    'work': ['work'],
    'wrong': ['ps'],
    '/logs/': ['to-sort'],
    'notes': ['notes'],
    'personalfinance': ['personalfinance'],
    'pictures': ['albums'],
    'jaeha': ['albums'],
    '/pictures/travel/': ['albums', 'travel'],
    'plans': ['journal'],
    'krx': ['to-sort'],
    'quickpost': ['journal', 'oneline'],
    'bookmarks': ['links'],
    'readinglist': ['links'],
    'trading': ['links'],
    'scrap': ['links'],
    'management': ['links'],
    'shop': ['to-sort'],
    'teach': ['talks'],
    '/writings/book/': ['to-sort'],
    'cs': ['dev'],
    'translations': ['dev'],
    'web': ['dev'],
    'gadgets': ['journal'],
    'trading': ['work'],
    'writings': ['to-sort'],
    'trip': ['travel'],
    '/ChapterEurope/': ['travel'],
    '/chicago/lake/': ['chicago', 'journal'],
    '/chicago/beer/': ['chicago', 'journal'],
    '/chicago/shopping/': ['chicago', 'journal'],
    '/chicago/restaurant/': ['chicago', 'journal'],
    '/chicago/foods/': ['chicago', 'food'],
    'bodytracking': ['bodytracking', 'journal'],
    '/ChapterEurope/rome/': ['travel'],
    '/ChapterEurope/rome_1/': ['travel'],
    '/ChapterEurope/rome_2/': ['travel'],
    '/ChapterEurope/rome_3/': ['travel'],
    'product': ['chicago', 'product'],
    'school': ['chicago', 'school'],
    'photo': ['chicago', 'albums'],
    'baby': ['baby', 'journal'],
    'travel': ['travel'],
    'atlanta': ['travel'],
    'BabyLog': ['baby'],
    'trivialmono': ['journal'],
    'trivial mono': ['journal', 'trivialmono'],
    'chicago': ['chicago', 'journal'],
}

def fetch_all(db, table, **where):
    c = db.cursor()
    where_clause = ""
    if where:
        where_clause = "WHERE " + " AND ".join(["%s=%s" % it for it in
            where.items()])

    c.execute("SELECT * FROM %s %s;" % (table, where_clause))
    return c.fetchall()

def process_body(body, file_id_mapping):
    body = body.replace('[more]', '[[more]]')
    body = body.replace('[kr]', '')
    body = body.replace('[en]', '')
    body = body.replace('[[[more]]]', '[[more]]')
    if '[more:' in body:
        a, b = body.split('[more:')
        p = b.index(']')
        c = b[:p]
        d = b[p+1:]
        body = a + c + '..\n[[more]]\n' + d

    def to_gfm(portion):
        lines = portion.group(0).splitlines()
        lang = lines[1].split(':')[1].strip()
        return '\n'.join(['```' + lang] + lines[2:-1] + ['```'])

    body = re.sub(r"^~~~~ *\nlang:.+?^~~~~ *$", to_gfm, body, flags=re.DOTALL | re.MULTILINE)
    body = re.sub(r"^~~~~$", "```", body, flags=re.MULTILINE)

    def fix_image(portion):
        link = portion.group(0).strip('{').strip('}').split('|')
        if len(link) == 1:
            link = link[0]
            cmt = ''
        else:
            link, cmt = link

        tokens = link.split('/') + ['3']
        get = tokens.index('get')
        no = int(tokens[get+1])
        sz = tokens[get+2]
        if no not in file_id_mapping: return portion.group(0)

        if not file_id_mapping[no].is_picture:
            cmt = cmt or path.basename(file_id_mapping[no].name)
            return r"""<a href="%s">%s</a>""" % (file_id_mapping[no].file.url,
                                                 cmt)

        if cmt:
            cmt = "\n\n" + cmt + "\n\n"

        if sz >= '2':
            return (r"""<a href="%s" class="lightbox-link attached-picture-full"><img src="%s"/></a>""" %
                    (file_id_mapping[no].file.url,
                    file_id_mapping[no].file.url)) + cmt

        return (r"""<a href="%s" class="lightbox-link"><img src="%s" class="legacy-thumbnail"/></a>""" %
                (file_id_mapping[no].file.url,
                file_id_mapping[no].thumbnail.url)) + cmt


    body = re.sub(r"{http://dazzling.pe.kr/upload/get/[^}]+?}", fix_image, body)

    return body

def md5file(file):
    md5 = hashlib.md5()
    md5.update(open(file, 'rb').read())
    return md5.hexdigest()

def truncate_chars(value, max_length):
    if len(value) > max_length:
        truncd_val = value[:max_length]
        if not len(value) == max_length+1 and value[max_length+1] != " ":
            truncd_val = truncd_val[:truncd_val.rfind(" ")]
        return truncd_val + "..."
    return value

def migrate_post(db, users, uploaded):
    dirs = fetch_all(db, 'jmk_directories')
    DIR_MAP = {}
    for dir in dirs:
        gg = TAGS_MAP.get(dir['full_path']) or TAGS_MAP.get(dir['name'])
        if gg is None:
            print dir['full_path']
            print dir['name']
            assert False
        DIR_MAP[dir['no']] = gg
    DIR_MAP[0] = ['journal']

    from collections import defaultdict
    files = list(fetch_all(db, 'jmk_files'))
    files_by_post = defaultdict(list)
    for f in files:
        files_by_post[f['page']].append(f)

    file_id_mapping = {}

    comments = list(fetch_all(db, 'jmk_comments'))
    comments.sort(key=lambda c: c['no'])
    comment_by_post = defaultdict(list)
    for c in comments:
        comment_by_post[c['page']].append(c)

    posts = list(fetch_all(db, 'jmk_pages'))
    posts.sort(key=lambda p: p['no'], reverse=False)
    print len(posts), 'posts'

    Post.objects.all().delete()
    Comment.objects.all().delete()
    Redirect.objects.all().delete()
    Attachment.objects.filter(original_link__startswith='http://jmk').delete()

    for i, post in enumerate(posts):
            
        print 'migrating', post['title'].encode('utf-8')
        for f in files_by_post[post['no']]:
            target_fn = fn = path.basename(f['path'])
            if len(fn) > 50:
                frag = fn.split('.')
                a = '.'.join(frag[:-1])
                b = frag[-1]
                target_fn = a[:50] + '.' + b
            fp = path.join(uploaded, fn)
            md5 = md5file(fp)
            dir = path.join('attachments', md5)
            dir_fs = path.join('../attachments', dir)
            if not path.exists(dir_fs):
                makedirs(dir_fs)
            target_path = path.join(dir_fs, target_fn)
            copyfile(fp, target_path)
            
            if f['is_image']:
                thumb_path = path.join(dir_fs, 'thumbnail.jpg')
                thumbnail_path = path.join(dir, 'thumbnail.jpg')
                save_thumbnail(thumb_path, open(fp, 'rb'))
                is_picture = True
            else:
                is_picture = False
                thumbnail_path = None

            print path.join(dir, fn)
            print thumbnail_path

            a = Attachment(is_picture=is_picture, 
                           date=f['uploaded'].date(),
                           timestamp=f['uploaded'],
                           file=path.join(dir, target_fn),
                           thumbnail=thumbnail_path,
                           original_link='http://jmk.pe.kr/upload/get/' +
                           str(f['no']))
            a.save()
            file_id_mapping[f['no']] = a

        print 'SLUG', post['name']
        if Post.objects.filter(slug=post['name']).count() > 0:
            for app in range(2,100):
                cand = post['name'] + '-' + str(app)
                print '   TRYING', cand
                if Post.objects.filter(slug=cand).count() == 0:
                    post['name'] = cand
                    break
        body = process_body(post['body'], file_id_mapping)
        if not post['title']:
            first_line = filter(lambda l: l, body.splitlines())[0].strip()
            first_line = re.sub(r'\[(.+?)\]\(.+?\)', lambda m: m.group(1), first_line)
            post['title'] = truncate_chars(first_line.strip('*').strip(), 30)

        p = Post(timestamp=post['created'],
                 dated=post['created'].date(),
                 permission=PERMISSION_MAP[post['protection']],
                 slug=post['name'],
                 title=post['title'],
                 body_public=body)
        p.save()
        p.timestamp = post['created']
        p.save()
        r = Redirect(from_url=post['full_path'], to_url=p.get_absolute_url())
        r.save()
        tags = DIR_MAP[post['directory']]
        if tags == ['travel'] and post['name'].startswith('pycon'):
            tags = ['dev']
        p.tags.add(*tags)

        for c in comment_by_post[post['no']]:
            kwargs = {'post': p, 
                      'parent': None, 
                      'comment': c['body'],
                      'name': c['author_name'],
                     }
            if c['author'] != -1 and c['author'] in users:
                kwargs['author'] = users[c['author']]
            else:
                kwargs['password'] = 'sha1$$' + (c['author_password'] or 'written_by_an_openid_user')

            cc = Comment(**kwargs)
            cc.save()
            cc.timestamp = c['dated']
            cc.save()
        
        # if i >= 500: break


def migrate_user(db):
    users = fetch_all(db, 'jmk_users')
    user_mapping = {}
    User.objects.all().delete()
    for i, user in enumerate(users):
        if user['password'] is None:
            print 'NOT MIGRATING user', user['nick']
            continue
        print 'migrating user', user['nick'], 'level', user['level']

        u = User.objects.create_user(username=user['nick'],
                                     password='blah',
                                     email=user['email'])
        u.password = 'sha1$$' + user['password']
        u.save()
        if user['level'] == 0:
            u.is_superuser = True
        elif user['level'] == 1:
            so, _ = Group.objects.get_or_create(name='SignificantOther')
            u.groups.add(so)
        elif user['level'] == 5:
            friends, _ = Group.objects.get_or_create(name='Friends')
            u.groups.add(friends)

        u.save()
        user_mapping[user['no']] = u
    return user_mapping




class Command(BaseCommand):
    args = '<host port, username password database uploaded models..>'
    help = 'Migrate data from old homepage'

    def handle(self, *args, **options):
        post_save.disconnect(sender=User, dispatch_uid='new_user')
        post_save.disconnect(sender=Comment, dispatch_uid='new_comment')
        host, port, user, password, db, uploaded = args[:6]
        models = args[6:]

        db = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=db,
                             cursorclass=MySQLdb.cursors.DictCursor,use_unicode=True,charset='utf8')

        users = {}
        if 'all' in models or 'users' in models:
            users = migrate_user(db)
        if 'all' in models or 'posts' in models:
            migrate_post(db, users, uploaded)



if __name__ == "__main__":
    pass
