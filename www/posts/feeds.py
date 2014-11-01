from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from models import Post, PUBLIC

class LatestEntriesFeed(Feed):
    title = u'jmk.pe.kr'
    link = '/'
    description = ''

    def items(self):
        return Post.objects.filter(permission=PUBLIC).order_by('-timestamp')[:5]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        template = get_template('render-post-excerpt.html')
        return template.render(Context({'post': item}))
