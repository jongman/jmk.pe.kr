from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from markdown import markdown as render_md

register = template.Library()

@register.filter
def render_post_excerpt(post):
    return mark_safe(post.render_excerpt())

@register.filter
def render_post(post, full):
    return mark_safe(post.render(full))

@register.filter
def markdown(text):
    return mark_safe(render_md(text))
