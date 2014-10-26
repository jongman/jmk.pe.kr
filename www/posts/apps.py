from django.apps import AppConfig

class PostsAppConfig(AppConfig):
    name = 'posts'
    def ready(self):
        import signals
