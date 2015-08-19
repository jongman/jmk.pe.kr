# -*- coding: utf-8 -*-
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.conf import settings
from random import choice
from markdown import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer, get_lexer_by_name
import urllib
import re

def get_security_question():
    return choice(settings.SECURITY_QUESTIONS)

def get_query(params):
    if not params: return ""
    return "?" + "&".join(["%s=%s" % (key, urllib.quote(val.encode("utf-8")))
                           for key, val in params.iteritems()])

class CalendarPaginator(object):
    def __init__(self, first_date, last_date, year, month, link_name, link_kwargs):
        year1, year2 = first_date.year, last_date.year
        month1, month2 = first_date.month, last_date.month

        year_range = range(min(year1, year), max(year2, year)+1)
        month_range = range(1, 13)

        lower = min((year1, month1), (year, month))
        upper = max((year2, month2), (year, month))

        self.months = [(y, m)
                       for y in year_range for m in month_range
                       if lower <= (y, m) <= upper]
        self.year = year
        self.month = month
        self.link_name = link_name
        self.link_kwargs = link_kwargs

    def get_link(self, year, month):
        self.link_kwargs.update({'year': year, 'month': month})
        return reverse(self.link_name, kwargs=self.link_kwargs)

    def render(self):
        ym = (self.year, self.month)
        if ym in self.months:
            index = self.months.index((self.year, self.month))
        else:
            index = len(self.months)
        links = [('%.4d/%.2d' % (y, m), self.get_link(y, m), (y, m) == ym)
                 for y, m in self.months]
        prev = self.get_link(*self.months[index-1]) if index > 0 else None
        next = self.get_link(*self.months[index+1]) if index+1 < len(self.months) else None
        return render_to_string("pagination-calendar.html",
                                {'links': links, 'prev': prev, 'next': next})

    def __unicode__(self):
        return self.render()


class Pagination(object):
    def __init__(self, paginator, page, link_name, link_kwargs, get_params):
        self.paginator = paginator
        self.page = page
        self.link_name = link_name
        self.link_kwargs = dict(link_kwargs)
        self.get_params = get_query(get_params)

    def link_with_page(self, page):
        self.link_kwargs["page"] = page
        return (reverse(self.link_name, kwargs=self.link_kwargs) +
                self.get_params)

    def render(self):
        num_pages = self.paginator.num_pages
        links = [(page_no, self.link_with_page(page_no), page_no == self.page.number)
                 for page_no in xrange(1, num_pages+1)]
        prev = self.link_with_page(self.page.number - 1) if self.page.number != 1 else None
        next = self.link_with_page(self.page.number + 1) if self.page.number != num_pages else None
        return render_to_string("pagination.html",
                                {"links": links, "prev": prev, "next": next, 
                                 "num_pages": num_pages})

    def __unicode__(self):
        return self.render()


def setup_paginator(objects, items_per_page, page, link_name, link_kwargs, get_params={}):
    paginator = Paginator(objects, items_per_page)
    try:
        page = paginator.page(page)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return Pagination(paginator, page, link_name, link_kwargs, get_params)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def apply_pygments(str):
    lines = str.splitlines()
    str = '\n'.join(lines[1:-1])
    first = lines[0].strip().lstrip('`')
    if first:
        lexer = get_lexer_by_name(first)
    else:
        lexer = guess_lexer(str)
    formatter = HtmlFormatter(style='colorful')
    return highlight(str, lexer, formatter)

def highlight_source_code(text):
    return re.sub('^```.*?\n.+?^```$', lambda match: apply_pygments(match.group(0)),
                  text, flags=re.DOTALL|re.MULTILINE)

def prepare_katex(str):
    return ''.join(['<span class="katex-inline">',
                    str.strip('$'),
                    '</span>'])

def process_katex(text):
    # replace escaped dollar signs
    text = text.replace(r'\$', '&#36;')
    return re.sub(ur'\$[^\$가-힣]+\$', lambda match: prepare_katex(match.group(0)), text)

# escape intra-word underscores
def escape_underscores(text):
    return re.sub(ur'[^\\\s]_[^\\\s]', 
                  lambda match: match.group(0).replace('_', r'\_'), text)

def render_classic(text):
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('\n', '<br/>')

    return '\n'.join(('<p>', text, '</p>'))

def render_text(text):
    if '!markdown!' not in text:
        return render_classic(text)
    else:
        text = text.replace('!markdown!', '')
        
    # simulate Github-Flavored Markdown
    text = highlight_source_code(text)
    # prepare text for Katex rendering
    text = process_katex(text)
    # escape underscores
    # text = escape_underscores(text)
    return markdown(text)


