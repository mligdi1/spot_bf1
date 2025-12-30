from django.apps import AppConfig


class SpotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'spot'
    
    def ready(self):
        import spot.signals