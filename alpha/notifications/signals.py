from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='appointments.Appointment')
def appointment_created_handler(sender, instance, created, **kwargs):
    """
    Send notification when appointment is created
    """
    if created and instance.status == 'booked':
        # Only send notifications if enabled in settings
        if getattr(settings, 'NOTIFICATIONS_ENABLED', True):
            from .tasks import send_appointment_booked_notification_task
            
            # Send notification asynchronously
            send_appointment_booked_notification_task.delay(
                appointment_id=instance.id,
                send_sms=getattr(settings, 'SEND_SMS_ON_BOOKING', True),
                send_email=getattr(settings, 'SEND_EMAIL_ON_BOOKING', True)
            )
            
            logger.info(f"Queued appointment booked notification for appointment {instance.id}")