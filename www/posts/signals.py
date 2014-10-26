from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from models import Comment
# from celery import shared_task, Celery
# 
# send_mail_task = shared_task(send_mail)
# 
# def send_mail_delay(*args, **kwargs):
#     send_mail_task.delay(*args, **kwargs)

# TODO: send emails in celery
@receiver(post_save, sender=User)
def new_user(sender, **kwargs):
    if kwargs.get('created'):
        instance = kwargs.get('instance')
        send_mail('JMK: New User %s' % instance.username.encode('utf-8'), 
                  'Email: %s' % instance.email,
                  settings.ADMIN_EMAIL, 
                  [settings.ADMIN_EMAIL])

@receiver(post_save, sender=Comment)
def new_comment(sender, **kwargs):
    recipients = set([settings.ADMIN_EMAIL])
    instance = kwargs.get('instance')
    if instance.parent and instance.parent.author:
        recipients.add(instance.parent.author.email)
    url = instance.post.get_absolute_url().encode('utf-8')
    cmt = instance.comment.encode('utf-8')
    send_mail('JMK: New Comment On "%s" by %s' % (instance.post.title.encode('utf-8'),
                                                  instance.name.encode('utf-8')),
                    '\n'.join(['Link: http://jmk.pe.kr%s#c%d' % (url, instance.pk),
                               '', cmt]),
                    settings.ADMIN_EMAIL,
                    recipients)
