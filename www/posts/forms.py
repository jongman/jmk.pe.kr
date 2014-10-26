# -*- coding: utf-8 -*-
from django import forms
from django.forms.widgets import PasswordInput
from django.contrib.auth.models import User
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

class SignUpForm(forms.Form):
    username = forms.CharField(label=u'사용자명', max_length=16)
    password = forms.CharField(label=u'비밀번호', max_length=128,
                               widget=PasswordInput)
    password_verify = forms.CharField(label=u'비밀번호 확인', max_length=128,
                                      widget=PasswordInput)
    email = forms.EmailField(label=u'이메일', max_length=128)

    def clean(self):
        password1 = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password_verify')
        if password1 and password1 != password2:
            raise forms.ValidationError(u'비밀번호 확인에 실패했습니다.')

        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(u'이미 존재하는 사용자입니다.')
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(u'이미 등록된 이메일 주소입니다.')
        return self.cleaned_data

