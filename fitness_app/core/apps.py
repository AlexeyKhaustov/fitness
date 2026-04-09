from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fitness_app.core'

    def ready(self):
        import fitness_app.core.signals