from django.apps import AppConfig


class CuentasappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'CuentasApp'
    
    def ready(self):
        import CuentasApp.signals