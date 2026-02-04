from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import NotificationLog, NotificationTemplate, ScheduledNotification


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'client', 'channel', 'status', 'subject', 
        'sent_at', 'created_at'
    ]
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['client__full_name', 'client__phone', 'client__email', 'message']
    readonly_fields = [
        'client', 'channel', 'subject', 'message', 'status', 
        'sent_at', 'delivered_at', 'appointment', 'sent_by', 
        'external_id', 'error_message', 'created_at'
    ]
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active', 'created_at']
    list_filter = ['notification_type', 'is_active', 'created_at']
    search_fields = ['name', 'sms_body', 'email_subject', 'email_body']
    
    fieldsets = (
        (_('Basic Info'), {
            'fields': ('name', 'notification_type', 'is_active')
        }),
        (_('SMS Template'), {
            'fields': ('sms_body',),
            'classes': ('collapse',)
        }),
        (_('Email Template'), {
            'fields': ('email_subject', 'email_body'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ScheduledNotification)
class ScheduledNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'appointment', 'notification_type', 'scheduled_for', 
        'sent', 'sent_at'
    ]
    list_filter = ['notification_type', 'sent', 'scheduled_for']
    search_fields = ['appointment__client__full_name']
    readonly_fields = [
        'appointment', 'notification_type', 'send_sms', 'send_email',
        'scheduled_for', 'sent', 'sent_at', 'celery_task_id', 'created_at'
    ]
    date_hierarchy = 'scheduled_for'
    
    def has_add_permission(self, request):
        return False