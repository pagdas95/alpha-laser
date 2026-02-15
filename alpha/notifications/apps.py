from django.apps import AppConfig

from django.utils.translation import gettext_lazy as _

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alpha.notifications'  # Full path for cookiecutter-django
    verbose_name = _('Notifications')
    
    def ready(self):
        # Import signals to register them using relative import
        from . import signals