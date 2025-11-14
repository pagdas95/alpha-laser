from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alpha.appointments'

    def ready(self):
        import alpha.appointments.signals
