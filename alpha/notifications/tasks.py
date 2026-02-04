from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


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
    Async task to send appointment reminder notification
    """
    try:
        from .services import notification_service
        from .models import ScheduledNotification
        Appointment = apps.get_model('appointments', 'Appointment')
        
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Check if appointment is still valid (not cancelled)
        if (appointment.status == 'cancelled'):
            logger.info(f"Skipping reminder for cancelled appointment {appointment_id}")
            return {'skipped': 'Appointment cancelled'}
        
        # Send the reminder
        result = notification_service.send_appointment_reminder(
            appointment=appointment,
            send_sms=send_sms,
            send_email=send_email
        )
        
        # Mark scheduled notification as sent
        ScheduledNotification.objects.filter(
            appointment=appointment,
            notification_type='24h_reminder',
            sent=False
        ).update(sent=True, sent_at=timezone.now())
        
        logger.info(f"Appointment reminder sent for appointment {appointment_id}")
        return result
        
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
        return {'error': 'Appointment not found'}
    except Exception as exc:
        logger.error(f"Error sending appointment reminder: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


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
    Periodic task to schedule 24-hour reminders for upcoming appointments
    Run this task every hour via Celery Beat
    """
    try:
        from .models import ScheduledNotification
        Appointment = apps.get_model('appointments', 'Appointment')
        
        # Get appointments starting in 24 hours (with a 1-hour window)
        now = timezone.now()
        reminder_time = now + timedelta(hours=24)
        window_start = reminder_time - timedelta(minutes=30)
        window_end = reminder_time + timedelta(minutes=30)
        
        # Find appointments that need reminders
        appointments = Appointment.objects.filter(
            start__gte=window_start,
            start__lte=window_end,
            status='booked'
        ).exclude(
            scheduled_notifications__notification_type='24h_reminder',
            scheduled_notifications__sent=True
        )
        
        scheduled_count = 0
        
        for appointment in appointments:
            # Check if reminder already scheduled
            if ScheduledNotification.objects.filter(
                appointment=appointment,
                notification_type='24h_reminder'
            ).exists():
                continue
            
            # Calculate when to send (24 hours before appointment)
            send_time = appointment.start - timedelta(hours=24)
            
            # Schedule the task
            task = send_appointment_reminder_task.apply_async(
                args=[appointment.id],
                kwargs={'send_sms': True, 'send_email': True},
                eta=send_time
            )
            
            # Create scheduled notification record
            ScheduledNotification.objects.create(
                appointment=appointment,
                notification_type='24h_reminder',
                scheduled_for=send_time,
                send_sms=True,
                send_email=True,
                celery_task_id=task.id
            )
            
            scheduled_count += 1
        
        logger.info(f"Scheduled {scheduled_count} appointment reminders")
        return {'scheduled': scheduled_count}
        
    except Exception as exc:
        logger.error(f"Error scheduling appointment reminders: {exc}")
        return {'error': str(exc)}


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