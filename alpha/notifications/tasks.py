from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

# Send the reminder this long before the appointment.
REMINDER_LEAD_TIME = timedelta(hours=24)
# Skip reminders for appointments booked less than this long before they start
# (matches the old behaviour, which only caught appointments booked ~24h ahead;
# same-day bookings already get the booking confirmation message).
REMINDER_MIN_BOOKING_LEAD = timedelta(hours=23)


# ✨✨✨ NEW: Variable replacement function ✨✨✨
def replace_variables(message, client):
    """
    Replace template variables with actual client data
    
    Variables:
    - {client_name}: Client's full name
    - {phone}: Client's phone number
    - {email}: Client's email address
    """
    if not message:
        return message
        
    replacements = {
        '{client_name}': client.full_name or '',
        '{phone}': client.phone or '',
        '{email}': client.email or '',
    }
    
    result = message
    for variable, value in replacements.items():
        result = result.replace(variable, value)
    
    return result
# ✨✨✨ END NEW FUNCTION ✨✨✨


@shared_task(bind=True, max_retries=3)
def send_appointment_booked_notification_task(self, appointment_id, send_sms=True, send_email=True):
    """
    Async task to send appointment booked notification
    """
    try:
        from .services import notification_service
        Appointment = apps.get_model('appointments', 'Appointment')
        
        appointment = Appointment.objects.get(id=appointment_id)
        result = notification_service.send_appointment_booked_notification(
            appointment=appointment,
            send_sms=send_sms,
            send_email=send_email
        )
        
        logger.info(f"Appointment booked notification sent for appointment {appointment_id}")
        return result
        
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
        return {'error': 'Appointment not found'}
    except Exception as exc:
        logger.error(f"Error sending appointment booked notification: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_appointment_reminder_task(self, appointment_id, send_sms=True, send_email=True):
    """
    Send the 24h reminder for one appointment.

    Idempotent: the ScheduledNotification row is "claimed" atomically
    (sent=False -> True) before sending, so duplicate deliveries of this task
    (beat re-dispatch, broker redelivery, old ETA tasks) never send twice.
    """
    from .services import notification_service
    from .models import ScheduledNotification
    Appointment = apps.get_model('appointments', 'Appointment')

    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
        return {'error': 'Appointment not found'}

    if appointment.status != 'booked':
        logger.info(f"Skipping reminder for appointment {appointment_id} (status={appointment.status})")
        return {'skipped': f'Appointment status {appointment.status}'}

    if appointment.start <= timezone.now():
        logger.info(f"Skipping reminder for appointment {appointment_id}: already started")
        return {'skipped': 'Appointment already started'}

    # Make sure a tracking row exists, then claim it atomically.
    notification, _ = ScheduledNotification.objects.get_or_create(
        appointment=appointment,
        notification_type='24h_reminder',
        defaults={
            'scheduled_for': appointment.start - REMINDER_LEAD_TIME,
            'send_sms': send_sms,
            'send_email': send_email,
        },
    )
    claimed = ScheduledNotification.objects.filter(
        pk=notification.pk, sent=False
    ).update(sent=True, sent_at=timezone.now())
    if not claimed:
        logger.info(f"Reminder for appointment {appointment_id} already sent, skipping")
        return {'skipped': 'Already sent'}

    try:
        result = notification_service.send_appointment_reminder(
            appointment=appointment,
            send_sms=send_sms,
            send_email=send_email
        )
    except Exception as exc:
        # Release the claim so a retry (or the next beat run) can send it.
        ScheduledNotification.objects.filter(pk=notification.pk).update(sent=False, sent_at=None)
        logger.error(f"Error sending appointment reminder {appointment_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    logger.info(f"Appointment reminder sent for appointment {appointment_id}")
    return result


@shared_task
def send_bulk_sms_task(client_ids, message, sent_by_id=None):
    """
    Async task to send bulk SMS
    ✨ NOW WITH VARIABLE REPLACEMENT! ✨
    """
    try:
        from .services import notification_service
        Client = apps.get_model('clients', 'Client')
        User = apps.get_model('users', 'User')
        
        clients = Client.objects.filter(id__in=client_ids)
        sent_by = User.objects.get(id=sent_by_id) if sent_by_id else None
        
        results = {'sent': 0, 'failed': 0, 'skipped': 0}
        
        for client in clients:
            if client.phone:
                # ✨ NEW: Replace variables for each client
                personalized_message = replace_variables(message, client)
                
                result = notification_service.send_sms(
                    phone=client.phone,
                    message=personalized_message,  # ✨ Use personalized message
                    client_obj=client,
                    sent_by=sent_by
                )
                if result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
            else:
                results['skipped'] += 1
        
        logger.info(f"Bulk SMS sent: {results}")
        return results
        
    except Exception as exc:
        logger.error(f"Error sending bulk SMS: {exc}")
        return {'error': str(exc)}


@shared_task
def send_bulk_email_task(client_ids, subject, message, html_message=None, sent_by_id=None):
    """
    Async task to send bulk email
    ✨ NOW WITH VARIABLE REPLACEMENT! ✨
    """
    try:
        from .services import notification_service
        Client = apps.get_model('clients', 'Client')
        User = apps.get_model('users', 'User')
        
        clients = Client.objects.filter(id__in=client_ids)
        sent_by = User.objects.get(id=sent_by_id) if sent_by_id else None
        
        results = {'sent': 0, 'failed': 0, 'skipped': 0}
        
        for client in clients:
            if client.email:
                # ✨ NEW: Replace variables for each client
                personalized_subject = replace_variables(subject, client)
                personalized_message = replace_variables(message, client)
                personalized_html = replace_variables(html_message, client) if html_message else None
                
                result = notification_service.send_email(
                    to_email=client.email,
                    subject=personalized_subject,  # ✨ Use personalized subject
                    message=personalized_message,  # ✨ Use personalized message
                    html_message=personalized_html,  # ✨ Use personalized HTML
                    client_obj=client,
                    sent_by=sent_by
                )
                if result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
            else:
                results['skipped'] += 1
        
        logger.info(f"Bulk email sent: {results}")
        return results
        
    except Exception as exc:
        logger.error(f"Error sending bulk email: {exc}")
        return {'error': str(exc)}


@shared_task
def schedule_appointment_reminders():
    """
    Periodic task (Celery Beat, every 10 minutes): dispatch 24h reminders that are due.

    A reminder is due when the appointment starts within the next 24 hours and no
    reminder has been sent yet. Reminders are dispatched immediately (no long ETA),
    so nothing piles up in worker memory, and if a run is missed (worker down,
    Redis hiccup) the next run catches up automatically.
    """
    from django.db.models import Exists, F, OuterRef
    from .models import ScheduledNotification
    Appointment = apps.get_model('appointments', 'Appointment')

    now = timezone.now()
    already_sent = ScheduledNotification.objects.filter(
        appointment=OuterRef('pk'),
        notification_type='24h_reminder',
        sent=True,
    )
    appointment_ids = list(
        Appointment.objects.filter(
            status='booked',
            start__gt=now,
            start__lte=now + REMINDER_LEAD_TIME,
            created_at__lte=F('start') - REMINDER_MIN_BOOKING_LEAD,
        )
        .exclude(Exists(already_sent))
        .values_list('id', flat=True)
    )

    for appointment_id in appointment_ids:
        # Safe to dispatch repeatedly: the task claims the reminder atomically.
        send_appointment_reminder_task.delay(appointment_id, send_sms=True, send_email=True)

    logger.info(f"Dispatched {len(appointment_ids)} appointment reminders")
    return {'dispatched': len(appointment_ids)}


@shared_task
def cleanup_old_notification_logs(days=90):
    """
    Clean up old notification logs
    Run this task daily via Celery Beat
    """
    try:
        from .models import NotificationLog
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = NotificationLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Deleted {deleted_count} old notification logs")
        return {'deleted': deleted_count}
        
    except Exception as exc:
        logger.error(f"Error cleaning up notification logs: {exc}")
        return {'error': str(exc)}