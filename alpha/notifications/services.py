import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

from .models import NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending SMS and Email notifications"""
    
    def __init__(self):
        # Initialize Twilio client
        self.twilio_client = None
        if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            try:
                self.twilio_client = TwilioClient(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
    
    # ✨ UPDATED: Helper method to get staff name from StaffProfile
    def _get_staff_name(self, staff):
        """
        Get staff display name with fallback options
        Works with your StaffProfile model structure
        
        Priority:
        1. staff.staff_profile.full_name (from StaffProfile)
        2. staff.name (if custom user model has name field)
        3. staff.get_full_name()
        4. staff.username
        5. "Our Team" (fallback)
        """
        if not staff:
            return "Our Team"
        
        # Try StaffProfile.full_name first (your main staff name)
        try:
            if hasattr(staff, 'staff_profile') and staff.staff_profile:
                profile_name = staff.staff_profile.full_name
                if profile_name and profile_name.strip():
                    return profile_name.strip()
        except Exception:
            pass  # StaffProfile doesn't exist or error accessing it
        
        # Try user.name field (if your user model has it)
        try:
            if hasattr(staff, 'name') and staff.name:
                return staff.name.strip()
        except Exception:
            pass
        
        # Try get_full_name() (first_name + last_name)
        try:
            full_name = staff.get_full_name()
            if full_name and full_name.strip() and full_name.strip() != "None None":
                return full_name.strip()
        except Exception:
            pass
        
        # Try first_name + last_name manually
        try:
            if hasattr(staff, 'first_name') and hasattr(staff, 'last_name'):
                first = staff.first_name or ""
                last = staff.last_name or ""
                name = f"{first} {last}".strip()
                if name and name != "None None":
                    return name
        except Exception:
            pass
        
        # Try username
        try:
            if hasattr(staff, 'username') and staff.username:
                return staff.username
        except Exception:
            pass
        
        # Fallback
        return "Our Team"
    
    def send_sms(
        self, 
        phone: str, 
        message: str, 
        client_obj=None, 
        appointment=None,
        sent_by=None
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio
        
        Args:
            phone: Phone number to send to
            message: Message body
            client_obj: Client instance
            appointment: Appointment instance
            sent_by: User who triggered the notification
            
        Returns:
            Dict with status and details
        """
        # Create log entry
        log = NotificationLog.objects.create(
            client=client_obj,
            channel='sms',
            message=message,
            status='pending',
            appointment=appointment,
            sent_by=sent_by
        )
        
        if not self.twilio_client:
            error_msg = "Twilio client not configured"
            log.status = 'failed'
            log.error_message = error_msg
            log.save()
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'log_id': log.id}
        
        if not hasattr(settings, 'TWILIO_PHONE_NUMBER'):
            error_msg = "TWILIO_PHONE_NUMBER not configured"
            log.status = 'failed'
            log.error_message = error_msg
            log.save()
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'log_id': log.id}
        
        try:
            # Format phone number (ensure it has + and country code)
            if not phone.startswith('+'):
                # Assuming Cyprus (+357) - adjust as needed
                phone = f"+357{phone.lstrip('0')}"
            
            # Send via Twilio
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone
            )
            
            # Update log
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.external_id = message_obj.sid
            log.save()
            
            logger.info(f"SMS sent successfully to {phone}. SID: {message_obj.sid}")
            
            return {
                'success': True,
                'message_sid': message_obj.sid,
                'log_id': log.id,
                'status': message_obj.status
            }
            
        except TwilioRestException as e:
            error_msg = f"Twilio error: {e.msg}"
            log.status = 'failed'
            log.error_message = error_msg
            log.save()
            logger.error(f"Failed to send SMS to {phone}: {error_msg}")
            return {'success': False, 'error': error_msg, 'log_id': log.id}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            log.status = 'failed'
            log.error_message = error_msg
            log.save()
            logger.error(f"Failed to send SMS to {phone}: {error_msg}")
            return {'success': False, 'error': error_msg, 'log_id': log.id}
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        client_obj=None,
        appointment=None,
        sent_by=None
    ) -> Dict[str, Any]:
        """
        Send email via Django email backend
        
        Args:
            to_email: Recipient email
            subject: Email subject
            message: Plain text message
            html_message: Optional HTML version
            client_obj: Client instance
            appointment: Appointment instance
            sent_by: User who triggered the notification
            
        Returns:
            Dict with status and details
        """
        # Create log entry
        log = NotificationLog.objects.create(
            client=client_obj,
            channel='email',
            subject=subject,
            message=message,
            status='pending',
            appointment=appointment,
            sent_by=sent_by
        )
        
        try:
            if html_message:
                # Send with HTML alternative
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[to_email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send()
            else:
                # Send plain text
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[to_email],
                    fail_silently=False,
                )
            
            # Update log
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            
            logger.info(f"Email sent successfully to {to_email}")
            
            return {
                'success': True,
                'log_id': log.id
            }
            
        except Exception as e:
            error_msg = f"Email error: {str(e)}"
            log.status = 'failed'
            log.error_message = error_msg
            log.save()
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            return {'success': False, 'error': error_msg, 'log_id': log.id}
    
    def send_appointment_booked_notification(self, appointment, send_sms=True, send_email=True):
        """
        Send notification when appointment is booked
        ✨ NOW RESPECTS CLIENT NOTIFICATION PREFERENCES ✨
        """
        client = appointment.client
        
        # Format message
        context = {
            'client_name': client.full_name,
            'date': appointment.start.strftime('%d/%m/%Y'),
            'time': appointment.start.strftime('%H:%M'),
            'service': appointment.service.name,
            'staff': self._get_staff_name(appointment.staff),  # ✨ FIXED: Uses StaffProfile.full_name
        }
        
        results = {'sms': None, 'email': None}
        
        # ✨ UPDATED: Check client preference for booking SMS
        if send_sms and client.phone and client.receive_booking_sms:
            sms_message = (
                f"Γεια σας {context['client_name']}! "
                f"Το ραντεβού σας επιβεβαιώθηκε για {context['date']} στις {context['time']}. "
                f"Υπηρεσία: {context['service']}. "
                f"Θα σας εξυπηρετήσει: {context['staff']}."
            )
            results['sms'] = self.send_sms(
                phone=client.phone,
                message=sms_message,
                client_obj=client,
                appointment=appointment,
                sent_by=appointment.created_by
            )
        elif send_sms and client.phone and not client.receive_booking_sms:
            # Log that we're skipping due to client preference
            logger.info(f"Skipping booking SMS for {client.full_name} (ID: {client.id}) - client preference disabled")
        
        # ✨ UPDATED: Check client preference for booking email
        if send_email and client.email and client.receive_booking_email:
            subject = f"Επιβεβαίωση Ραντεβού - {context['date']} {context['time']}"
            
            # Plain text version
            plain_message = (
                f"Αγαπητέ/ή {context['client_name']},\n\n"
                f"Το ραντεβού σας έχει επιβεβαιωθεί!\n\n"
                f"Λεπτομέρειες:\n"
                f"📅 Ημερομηνία: {context['date']}\n"
                f"🕐 Ώρα: {context['time']}\n"
                f"💆 Υπηρεσία: {context['service']}\n"
                f"👤 Θεραπευτής: {context['staff']}\n\n"
                f"Σας περιμένουμε!\n"
            )
            
            # HTML version
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #4CAF50;">Επιβεβαίωση Ραντεβού</h2>
                    <p>Αγαπητέ/ή <strong>{context['client_name']}</strong>,</p>
                    <p>Το ραντεβού σας έχει επιβεβαιωθεί!</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>📅 Ημερομηνία:</strong> {context['date']}</p>
                        <p style="margin: 5px 0;"><strong>🕐 Ώρα:</strong> {context['time']}</p>
                        <p style="margin: 5px 0;"><strong>💆 Υπηρεσία:</strong> {context['service']}</p>
                        <p style="margin: 5px 0;"><strong>👤 Θεραπευτής:</strong> {context['staff']}</p>
                    </div>
                    
                    <p>Σας περιμένουμε!</p>
                    <p style="color: #777; font-size: 12px; margin-top: 30px;">
                        Αν θέλετε να ακυρώσετε ή να μεταφέρετε το ραντεβού σας, παρακαλούμε επικοινωνήστε μαζί μας.
                    </p>
                </div>
            </body>
            </html>
            """
            
            results['email'] = self.send_email(
                to_email=client.email,
                subject=subject,
                message=plain_message,
                html_message=html_message,
                client_obj=client,
                appointment=appointment,
                sent_by=appointment.created_by
            )
        elif send_email and client.email and not client.receive_booking_email:
            # Log that we're skipping due to client preference
            logger.info(f"Skipping booking email for {client.full_name} (ID: {client.id}) - client preference disabled")
        
        return results
    
    def send_appointment_reminder(self, appointment, send_sms=True, send_email=True):
        """
        Send reminder notification before appointment
        ✨ NOW RESPECTS CLIENT NOTIFICATION PREFERENCES ✨
        """
        client = appointment.client
        
        context = {
            'client_name': client.full_name,
            'date': appointment.start.strftime('%d/%m/%Y'),
            'time': appointment.start.strftime('%H:%M'),
            'service': appointment.service.name,
            'staff': self._get_staff_name(appointment.staff),  # ✨ FIXED: Uses StaffProfile.full_name
        }
        
        results = {'sms': None, 'email': None}
        
        # ✨ UPDATED: Check client preference for reminder SMS
        if send_sms and client.phone and client.receive_reminder_sms:
            sms_message = (
                f"Υπενθύμιση! {context['client_name']}, "
                f"έχετε ραντεβού αύριο {context['date']} στις {context['time']}. "
                f"Υπηρεσία: {context['service']}. Σας περιμένουμε!"
            )
            results['sms'] = self.send_sms(
                phone=client.phone,
                message=sms_message,
                client_obj=client,
                appointment=appointment
            )
        elif send_sms and client.phone and not client.receive_reminder_sms:
            # Log that we're skipping due to client preference
            logger.info(f"Skipping reminder SMS for {client.full_name} (ID: {client.id}) - client preference disabled")
        
        # ✨ UPDATED: Check client preference for reminder email
        if send_email and client.email and client.receive_reminder_email:
            subject = f"Υπενθύμιση Ραντεβού - {context['date']} {context['time']}"
            
            plain_message = (
                f"Αγαπητέ/ή {context['client_name']},\n\n"
                f"Θέλουμε να σας υπενθυμίσουμε το ραντεβού σας:\n\n"
                f"📅 Ημερομηνία: {context['date']}\n"
                f"🕐 Ώρα: {context['time']}\n"
                f"💆 Υπηρεσία: {context['service']}\n"
                f"👤 Θεραπευτής: {context['staff']}\n\n"
                f"Σας περιμένουμε!\n"
            )
            
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #FF9800;">⏰ Υπενθύμιση Ραντεβού</h2>
                    <p>Αγαπητέ/ή <strong>{context['client_name']}</strong>,</p>
                    <p>Θέλουμε να σας υπενθυμίσουμε το ραντεβού σας!</p>
                    
                    <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #FF9800;">
                        <p style="margin: 5px 0;"><strong>📅 Ημερομηνία:</strong> {context['date']}</p>
                        <p style="margin: 5px 0;"><strong>🕐 Ώρα:</strong> {context['time']}</p>
                        <p style="margin: 5px 0;"><strong>💆 Υπηρεσία:</strong> {context['service']}</p>
                        <p style="margin: 5px 0;"><strong>👤 Θεραπευτής:</strong> {context['staff']}</p>
                    </div>
                    
                    <p>Σας περιμένουμε!</p>
                </div>
            </body>
            </html>
            """
            
            results['email'] = self.send_email(
                to_email=client.email,
                subject=subject,
                message=plain_message,
                html_message=html_message,
                client_obj=client,
                appointment=appointment
            )
        elif send_email and client.email and not client.receive_reminder_email:
            # Log that we're skipping due to client preference
            logger.info(f"Skipping reminder email for {client.full_name} (ID: {client.id}) - client preference disabled")
        
        return results
    
    def send_bulk_notification(
        self,
        clients: List,
        message: str,
        subject: str = "",
        html_message: Optional[str] = None,
        send_sms: bool = True,
        send_email: bool = True,
        sent_by=None
    ) -> Dict[str, Any]:
        """
        Send bulk notifications to multiple clients
        
        Returns:
            Dict with success/failure counts
        """
        results = {
            'sms': {'sent': 0, 'failed': 0, 'skipped': 0},
            'email': {'sent': 0, 'failed': 0, 'skipped': 0},
            'total_clients': len(clients)
        }
        
        for client in clients:
            # Send SMS
            if send_sms:
                if client.phone:
                    sms_result = self.send_sms(
                        phone=client.phone,
                        message=message,
                        client_obj=client,
                        sent_by=sent_by
                    )
                    if sms_result['success']:
                        results['sms']['sent'] += 1
                    else:
                        results['sms']['failed'] += 1
                else:
                    results['sms']['skipped'] += 1
            
            # Send Email
            if send_email:
                if client.email:
                    email_result = self.send_email(
                        to_email=client.email,
                        subject=subject,
                        message=message,
                        html_message=html_message,
                        client_obj=client,
                        sent_by=sent_by
                    )
                    if email_result['success']:
                        results['email']['sent'] += 1
                    else:
                        results['email']['failed'] += 1
                else:
                    results['email']['skipped'] += 1
        
        return results


# Singleton instance
notification_service = NotificationService()