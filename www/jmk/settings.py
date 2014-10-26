"""
Django settings for jmk project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

ADMIN_EMAIL = 'jongman@gmail.com'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ''
from local_settings import SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'djcelery_email',

    'taggit',

    'posts'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

# TEMPLATE_CONTEXT_PROCESSORS = (
#     'django.core.context_processors.request',
# )

ROOT_URLCONF = 'jmk.urls'

WSGI_APPLICATION = 'jmk.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'jmk',
        'USER': 'vagrant',
        'HOST': '',
        'PORT': '',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_L10N = True

USE_TZ = True

MEDIA_URL = '/media/'
MEDIA_ROOT = '/vagrant/attachments/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

class InvalidVarException(object):
    def __mod__(self, missing):
        try:
            missing_str=unicode(missing)
        except:
            missing_str='Failed to create string representation'
        raise Exception('Unknown template variable %r %s' % (missing, missing_str))
    def __contains__(self, search):
        if search=='%s':
            return True
        return False

TEMPLATE_DEBUG=True
TEMPLATE_STRING_IF_INVALID = InvalidVarException()

SMUGMUG_SIZE = 'X3Large'
SMUGMUG_SYNC_CATEGORY = 'Archive'

from local_settings import *
from hashlib import md5

for q in SECURITY_QUESTIONS:
    q['md5'] = md5(q['answer'].encode('utf-8')).hexdigest()

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
