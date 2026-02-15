from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationTemplate(models.Model):
    """Reusable templates for notifications"""
    NOTIFICATION_TYPE_CHOICES = [
        ('appointment_booked', _('Appointment Booked')),
        ('appointment_reminder', _('Appointment Reminder')),
        ('custom', _('Custom Message')),
    ]
    
    name = models.CharField(_("Template Name"), max_length=100)
    notification_type = models.CharField(
        _("Type"), 
        max_length=30, 
        choices=NOTIFICATION_TYPE_CHOICES,
        default='custom'
    )
    
    # SMS Template
    sms_body = models.TextField(
        _("SMS Body"), 
        blank=True,
        help_text=_("Available variables: {client_name}, {date}, {time}, {service}, {staff}")
    )
    
    # Email Template
    email_subject = models.CharField(_("Email Subject"), max_length=200, blank=True)
    email_body = models.TextField(
        _("Email Body"), 
        blank=True,
        help_text=_("Available variables: {client_name}, {date}, {time}, {service}, {staff}")
    )
    
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"


class NotificationLog(models.Model):
    """Log all notifications sent"""
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
        ('delivered', _('Delivered')),
    ]
    
    # Who
    client = models.ForeignKey(
        'clients.Client', 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    # What
    channel = models.CharField(_("Channel"), max_length=10, choices=CHANNEL_CHOICES)
    subject = models.CharField(_("Subject"), max_length=200, blank=True)
    message = models.TextField(_("Message"))
    
    # When & Status
    status = models.CharField(
        _("Status"), 
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    sent_at = models.DateTimeField(_("Sent At"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("Delivered At"), null=True, blank=True)
    
    # Tracking
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_sent'
    )
    
    # External IDs (for tracking with providers)
    external_id = models.CharField(
        _("External ID"), 
        max_length=100, 
        blank=True,
        help_text=_("Twilio Message SID or Email Message ID")
    )
    
    # Error tracking
    error_message = models.TextField(_("Error Message"), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Notification Log")
        verbose_name_plural = _("Notification Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['appointment']),
        ]
    
    def __str__(self):
        return f"{self.channel} to {self.client} - {self.status}"


class ScheduledNotification(models.Model):
    """Track scheduled notifications (like 24h reminders)"""
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='scheduled_notifications'
    )
    
    notification_type = models.CharField(
        _("Type"),
        max_length=30,
        choices=[
            ('24h_reminder', _('24 Hour Reminder')),
            ('2h_reminder', _('2 Hour Reminder')),
            ('followup', _('Follow-up')),
        ]
    )
    
    send_sms = models.BooleanField(_("Send SMS"), default=True)
    send_email = models.BooleanField(_("Send Email"), default=True)
    
    scheduled_for = models.DateTimeField(_("Scheduled For"))
    sent = models.BooleanField(_("Sent"), default=False)
    sent_at = models.DateTimeField(_("Sent At"), null=True, blank=True)
    
    celery_task_id = models.CharField(
        _("Celery Task ID"),
        max_length=100,
        blank=True,
        help_text=_("ID of the scheduled Celery task")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Scheduled Notification")
        verbose_name_plural = _("Scheduled Notifications")
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['scheduled_for', 'sent']),
            models.Index(fields=['appointment']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} for {self.appointment} at {self.scheduled_for}"