# -*- coding: utf-8 -*-
from django import forms
from models import Post
from datetime import date

class WriteForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'tags', 'body_public', 'body_private', 
                  'dated', 'permission', 'album_type']

    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        if 'instance' not in kwargs:
            self.initial['dated'] = date.today().strftime('%Y-%m-%d')
            # instance = kwargs['instance']
            # self.initial['categories'] = ','.join(category.slug for category in
            #                                       instance.category_set.all())




