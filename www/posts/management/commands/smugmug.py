# -*- coding: utf-8 -*-

import re, urllib, urllib2, urlparse, hashlib
import json, logging
import requests
from os import path, makedirs
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from posts.models import Attachment
from datetime import date, datetime

API_VERSION='1.2.2'
API_URL='https://secure.smugmug.com/services/api/json/1.2.2/'
UPLOAD_URL='http://upload.smugmug.com/'

YYYYMMDD = re.compile('^\d{4}-\d{2}-\d{2}$')

class SmugmugException(Exception):
    def __init__(self, response):
        self.response = response
        super(Exception, self).__init__()
    pass

class API(object):
    def __init__(self, api_key, id, password):
        self.session = None
        self.cookie = {}
        self.api_key = api_key
        self.id = id
        self.password = password

    def login(self):
        res = self._call("smugmug.login.withPassword",
                {"APIKey": self.api_key,
                 "EmailAddress": self.id,
                 "Password": self.password})
        self.session = res["Login"]["Session"]["id"]

    def change_album_setting(self, album_id, args={}):
        args = dict(args)
        args["AlbumID"] = album_id
        return self._call("smugmug.albums.changeSettings", args)

    def get_albums(self):
        return self._call("smugmug.albums.get")["Albums"]

    def get_images(self, album_id, album_key, args={}):
        args["AlbumID"] = album_id
        args["AlbumKey"] = album_key
        return self._call("smugmug.images.get", args)["Album"]["Images"]

    def get_image_info(self, image_id, image_key):
        return self._call("smugmug.images.getInfo",
                          {"ImageID": image_id, "ImageKey": image_key})

    def delete_image(self, image_id):
        return self._call("smugmug.images.delete",
                          {"ImageID": image_id})
    def delete_album(self, album_id):
        return self._call("smugmug.albums.delete",
                          {"AlbumID": album_id})

    def change_image_setting(self, image_id, args={}):
        args = dict(args)
        args["ImageID"] = image_id
        return self._call("smugmug.images.changeSettings", args)

    def get_categories(self):
        cate = self._call("smugmug.categories.get")
        return dict((d["Name"], d["id"]) for d in cate["Categories"])

    def get_subcategories(self, category_id):
        try:
            cate = self._call("smugmug.subcategories.get",
                    {"CategoryID": category_id})
            return dict((d["Name"], d["id"]) for d in cate["SubCategories"])
        except SmugmugException as e:
            resp = e.response
            if isinstance(resp, dict) and resp["code"] == 15:
                return []
            raise

    def create_subcategory(self, category_id, name):
        logging.info("Creating subcategory %s ..", name)
        return self._call("smugmug.subcategories.create",
                {"CategoryID": category_id, "Name":
                    name})["SubCategory"]["id"]

    def create_album(self, name, category, options={}):
        options.update({"Title": name, "CategoryID": category})
        logging.debug("create_album %s", str(options))
        ret = self._call("smugmug.albums.create", options)["Album"]
        return (ret['Key'], ret['id'])

    def download(self, url, target):
        req = requests.get(url, cookies=self.cookie)
        with open(target, 'wb') as fp:
            for chunk in req.iter_content(1024*1024):
                fp.write(chunk)

    def _call(self, method, params={}):
        params = dict(params)
        if self.session and "SessionID" not in params:
            params["SessionID"] = self.session
        params['method'] = method

        ret = requests.get(API_URL, params=params, cookies=self.cookie)
        self.cookie.update(ret.cookies.get_dict())
        return ret.json()

    def _http_request(self, request):
        for it in xrange(5):
            try:
                response_obj = urllib2.urlopen(request)
                response = response_obj.read()
                result = json.loads(response)

                meta_info = response_obj.info()
                if meta_info.has_key("set-cookie"):
                    match = re.search('(_su=\S+);', meta_info["set-cookie"])
                    if match and match.group(1) != "_su=deleted":
                        self.su_cookie = match.group(1)
                if result["stat"] != "ok":
                    raise SmugmugException(result)
                return result
            except:
                raise
            # except SmugmugException as e:
            #     logging.error("SmugmugException: %s", str(e.response))
            #     raise
            # except Exception as e:
            #     logging.error("Exception during request: %s", str(e))
            #     continue
        logging.info("API request failed. Request was:\n%s\n"
                "Response was:\n%s", request.get_full_url(),
                str(response))
        raise SmugmugException(response)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--earliest', default=None, help='YYYY-MM-DD'),
        make_option('--latest', default=None, help='YYYY-MM-DD'),
        make_option('--full', default=False, action='store_true', dest='full'))
    help = 'Pull Attachments from Smugmug'

    def sync_album(self, album_info):
        print 'Syncing album %s ..' % album_info
        images = self.api.get_images(album_info['id'], album_info['Key'],
                                     {'Heavy': True})

        updated = False

        dated = date(*map(int, album_info['Title'].split('-')))
        existing = Attachment.objects.filter(date=dated)
        synced_urls = set(e.original_link for e in existing)
        for image in images:
            if image['URL'] in synced_urls: continue
            if image['Format'] not in ('JPG', 'PNG'): continue
            md5 = image['MD5Sum']
            print 'Downloading', image, '..'

            file_path = path.join('attachments', md5, image['FileName'])
            thumb_path  = path.join('attachments', md5, 'thumbnail.jpg')

            self.download(image[settings.SMUGMUG_SIZE + 'URL'], 
                          path.join(settings.MEDIA_ROOT, file_path))
            self.download(image['ThumbURL'], 
                          path.join(settings.MEDIA_ROOT, thumb_path))

            timestamp = datetime.strptime(image['Date'], '%Y-%m-%d %H:%M:%S')
            attachment = Attachment(is_picture=True, 
                                    date=dated,
                                    timestamp=timestamp,
                                    file=file_path,
                                    thumbnail=thumb_path,
                                    original_link=image['URL'])
            attachment.save()
            attachment.timestamp = timestamp
            updated = True
        return updated

    def download(self, url, target):
        if path.exists(target):
            print 'target path', target, 'already exists'
            return
        dir = path.dirname(target)
        if not path.exists(dir):
            makedirs(dir)
        print 'downloading to', target, '..'
        self.api.download(url, target)

    def handle(self, *args, **options):

        print 'Logging in ..'
        api = API(settings.SMUGMUG_APIKEY, settings.SMUGMUG_USERID,
                  settings.SMUGMUG_PASSWORD)
        self.api = api

        api.login()

        print 'Listing albums ..'
        albums = api.get_albums()
        print 'Found %d albums.' % len(albums)

        filtered = [album 
                    for album in albums 
                    if album.get('Category', {}).get('Name') == settings.SMUGMUG_SYNC_CATEGORY and
                    (options['earliest'] == None or album['Title'] >= options['earliest']) and
                    (options['latest'] == None or album['Title'] <= options['latest']) and
                    YYYYMMDD.match(album['Title'])]
        if not options['full']:
            filtered = filtered[:10]
        print 'Will sync %d albums.' % len(filtered)
        filtered.sort(key=lambda a: a['Title'], reverse=True)

        for album in filtered:
            self.sync_album(album)

if __name__ == "__main__":
    api = API('api key', 
              'email',
              'password')
    api.login()
    print api.get_albums()
