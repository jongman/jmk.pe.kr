from django.conf.urls import patterns, url
import views
import feeds

urlpatterns = patterns(
    'posts.views',

    url(r'^/?$', views.timeline),
    url(r'^timeline/?$', views.timeline, name='timeline'),
    url(r'^timeline/(?P<page>\d+)$', views.timeline, name='timeline'),
    url(r'^category/(?P<category>[^/]+)/timeline/?$', views.timeline, name='timeline'),
    url(r'^category/(?P<category>[^/]+)/timeline/(?P<page>\d+)$', views.timeline, name='timeline'),
    url(r'^head/(?P<category>[^/]+)$', views.category_first, name='head'),

    url(r'^list/?$', views.list_posts, name='list'),
    url(r'^list/(?P<page>\d+)$', views.list_posts, name='list'),
    url(r'^category/(?P<category>[^/]+)/list/?$', views.list_posts, name='list'),
    url(r'^category/(?P<category>[^/]+)/list/(?P<page>\d+)$', views.list_posts, name='list'),

    url(r'^calendar/?$', views.calendar, name='calendar'),
    url(r'^calendar/(?P<year>\d{4})/(?P<month>\d{1,2})/?$', views.calendar, name='calendar'),
    url(r'^category/(?P<category>[^/]+)/calendar/?$', views.calendar, name='calendar'),
    url(r'^category/(?P<category>[^/]+)/calendar/(?P<year>\d{4})/(?P<month>\d{1,2})/?$', views.calendar, name='calendar'),

    url(r'^user/(?P<id>\d+)$', views.user, name='user-details'),

    url(r'^read/(?P<slug>.+)$', views.read, name='post-read'),
    url(r'^full/(?P<slug>.+)$', views.read, name='post-read-full',
        kwargs={'album_type': 'full'}),
    url(r'^thumbnails/(?P<slug>.+)$', views.read, name='post-read-thumbnails',
        kwargs={'album_type': 'thumbnails'}),

    url(r'^write/$', views.write, name='post-write'),
    url(r'^write/(?P<id>\d+)$', views.write, name='post-write'),
    url(r'^write/album/$', views.write_album, name='post-album'),
    url(r'^write/journal//?$',
        views.write_journal, name='write-journal'),
    url(r'^write/journal/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/?$',
        views.write_journal, name='write-journal'),

    url(r'^delete/(?P<id>\d+)$', views.delete, name='post-delete'),
    url(r'^post-comment/$', views.post_comment,
        name='post-comment'),
    url(r'^delete-comment/(?P<id>\d+)$', views.delete_comment,
        name='delete-comment'),
    url(r'^categories/$', views.categories, name='categories'),

    url(r'^gallery/$', views.gallery, name='gallery'),

    url(r'^new-attachment/$', views.new_attachment, name='new-attachment'),
    url(r'^list-attachment-folders/$', views.list_attachment_folders, name='list-attachment-folders'),
    url(r'^list-attachment/$', views.list_attachment, name='list-attachment'),
    url(r'^set-attachment-state/$', views.set_attachment_state,
        name='set-attachment-state'),

    url(r'^login/$', views.login, name='login'),
    url(r'^lost-password/$', views.lost_password, name='lost-password'),
    url(r'^reset-password/(?P<uuid>.+)$', views.reset_password, name='reset-password'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^logout/$', views.logout, name='logout'),

    url(r'^search/$', views.search, name='search'),
    url(r'^search/(?P<page>\d+)$', views.search, name='search'),

    url(r'^pages/read/(?P<page>.+)$', views.redirect_legacy_link),

    url(r'^feed/$', feeds.LatestEntriesFeed()),


)
