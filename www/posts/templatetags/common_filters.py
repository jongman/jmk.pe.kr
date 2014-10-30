# -*- coding: utf-8 -*-
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.conf import settings
from posts.utils import render_text

register = template.Library()

@register.filter
def render_post_excerpt(post):
    return mark_safe(post.render_excerpt())

@register.filter
def render_post(post, full):
    return mark_safe(post.render(full))

@register.filter
def markdown(text):
    return mark_safe(render_text(text))

@register.filter
def newline_to_br(text):
    return mark_safe(text.replace('\n', '<br/>\n'))

@register.filter
def render_security_question(question):
    fragments = []
    if 'before' in question: 
        fragments.append(question['before'])
    fragments.append((ur"<input type='text' class='security' data-md5='%s'"
                      "placeholder='%s' name='security'/>") %
                     (question['md5'], 
                      question.get('placeholder', u'채워주세요')))
    if 'after' in question: 
        fragments.append(question['after'])
    return mark_safe(u' '.join(fragments))
