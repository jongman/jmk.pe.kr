from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from models import Comment
from django.template.loader import get_template
from django.template import Context
# from celery import shared_task, Celery
# 
# send_mail_task = shared_task(send_mail)
# 
# def send_mail_delay(*args, **kwargs):
#     send_mail_task.delay(*args, **kwargs)

# TODO: send emails in celery
@receiver(post_save, sender=User, dispatch_uid='new_user')
def new_user(sender, **kwargs):
    if kwargs.get('created'):
        instance = kwargs.get('instance')
        send_mail('JMK: New User %s' % instance.username.encode('utf-8'), 
                  'Email: %s' % instance.email,
                  settings.ADMIN_EMAIL, 
                  [settings.ADMIN_EMAIL])

@receiver(post_save, sender=Comment, dispatch_uid='new_comment')
def new_comment(sender, **kwargs):
    recipients = set()
    instance = kwargs.get('instance')

    if not instance.author or not instance.author.is_superuser:
        recipients.add(settings.ADMIN_EMAIL)
    if instance.parent and instance.parent.author:
        recipients.add(instance.parent.author.email)

    email_template = get_template('comment-email.txt')
    body = email_template.render(Context({'comment': instance}))
    subject = 'JMK: New Comment On "%s" by %s' % (instance.post.title,
                                                  instance.name)
    send_mail(subject.encode('utf-8'), body.encode('utf-8'),
              settings.ADMIN_EMAIL, recipients)
