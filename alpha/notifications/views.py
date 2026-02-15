from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404  # ✨ ADDED get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
import json

from .forms import BulkNotificationForm, ClientSelectionForm, NotificationTemplateForm  # ✨ ADDED NotificationTemplateForm
from .models import NotificationLog, NotificationTemplate, ScheduledNotification
from .tasks import send_bulk_sms_task, send_bulk_email_task


@login_required
@permission_required('notifications.add_notificationlog', raise_exception=True)
def bulk_notification_view(request):
    """
    View for sending bulk notifications to clients
    """
    from django.apps import apps
    Client = apps.get_model('clients', 'Client')
    
    # Get all clients
    clients = Client.objects.all().order_by('full_name')
    
    # Apply filters if any
    search_query = request.GET.get('search', '')
    has_email = request.GET.get('has_email') == 'on'
    has_phone = request.GET.get('has_phone') == 'on'
    
    if search_query:
        clients = clients.filter(
            Q(full_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if has_email:
        clients = clients.exclude(email='')
    
    if has_phone:
        clients = clients.exclude(phone='')
    
    if request.method == 'POST':
        print("📝 POST REQUEST RECEIVED")
        print(f"POST data: {request.POST}")
        
        form = BulkNotificationForm(request.POST)
        
        print(f"Form valid: {form.is_valid()}")
        
        if form.is_valid():
            print("✅ FORM IS VALID")
            
            notification_type = form.cleaned_data['notification_type']
            send_to_all = form.cleaned_data['send_to_all']
            selected_clients_json = form.cleaned_data.get('selected_clients', '[]')
            
            # Determine which clients to send to
            if send_to_all:
                target_clients = list(clients.values_list('id', flat=True))
            else:
                try:
                    target_clients = json.loads(selected_clients_json)
                except json.JSONDecodeError:
                    messages.error(request, _("Invalid client selection"))
                    return redirect('notifications:bulk-send')
            
            if not target_clients:
                messages.error(request, _("No clients selected"))
                return redirect('notifications:bulk-send')
            
            # Send notifications based on type
            tasks_queued = []
            
            if notification_type in ['sms', 'both']:
                sms_message = form.cleaned_data['sms_message']
                print(f"Queuing SMS task for {len(target_clients)} clients")
                task = send_bulk_sms_task.delay(
                    client_ids=target_clients,
                    message=sms_message,
                    sent_by_id=request.user.id
                )
                tasks_queued.append('SMS')
                print(f"SMS task queued: {task.id}")
            
            if notification_type in ['email', 'both']:
                email_subject = form.cleaned_data['email_subject']
                email_message = form.cleaned_data['email_message']
                print(f"Queuing email task for {len(target_clients)} clients")
                task = send_bulk_email_task.delay(
                    client_ids=target_clients,
                    subject=email_subject,
                    message=email_message,
                    sent_by_id=request.user.id
                )
                tasks_queued.append('Email')
                print(f"Email task queued: {task.id}")
            
            messages.success(
                request,
                _(f"{' and '.join(tasks_queued)} notifications are being sent to {len(target_clients)} clients. "
                  f"This may take a few minutes.")
            )
            
            return redirect('notifications:logs')
        else:
            print(f"❌ FORM ERRORS: {form.errors}")
            
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
            
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = BulkNotificationForm()
    
    context = {
        'form': form,
        'clients': clients,
        'client_count': clients.count(),
        'search_form': ClientSelectionForm(request.GET),
        'templates': NotificationTemplate.objects.filter(is_active=True),  # ✨ ADDED: Pass templates to context
    }
    
    return render(request, 'notifications/bulk_send.html', context)


# ✨✨✨ NEW VIEWS FOR TEMPLATE MANAGEMENT ✨✨✨

@login_required
@permission_required('notifications.add_notificationtemplate', raise_exception=True)
def template_list_view(request):
    """
    View to list all notification templates
    """
    templates = NotificationTemplate.objects.filter(is_active=True).order_by('-created_at')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'notifications/template_list.html', context)


@login_required
@permission_required('notifications.add_notificationtemplate', raise_exception=True)
def template_create_view(request):
    """
    View to create a new notification template
    """
    if request.method == 'POST':
        form = NotificationTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, _(f'Template "{template.name}" created successfully!'))
            return redirect('notifications:templates')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = NotificationTemplateForm()
    
    context = {
        'form': form,
        'title': _('Create Notification Template'),
        'submit_text': _('Create Template'),
    }
    
    return render(request, 'notifications/template_form.html', context)


@login_required
@permission_required('notifications.change_notificationtemplate', raise_exception=True)
def template_edit_view(request, pk):
    """
    View to edit an existing notification template
    """
    template = get_object_or_404(NotificationTemplate, pk=pk)
    
    if request.method == 'POST':
        form = NotificationTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save()
            messages.success(request, _(f'Template "{template.name}" updated successfully!'))
            return redirect('notifications:templates')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = NotificationTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'title': _(f'Edit Template: {template.name}'),
        'submit_text': _('Update Template'),
    }
    
    return render(request, 'notifications/template_form.html', context)


@login_required
@permission_required('notifications.delete_notificationtemplate', raise_exception=True)
def template_delete_view(request, pk):
    """
    View to delete a notification template
    """
    template = get_object_or_404(NotificationTemplate, pk=pk)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, _(f'Template "{template_name}" deleted successfully!'))
        return redirect('notifications:templates')
    
    context = {
        'template': template,
    }
    
    return render(request, 'notifications/template_confirm_delete.html', context)


@login_required
def template_get_api(request, pk):
    """
    API endpoint to get template data for auto-filling forms (AJAX)
    """
    template = get_object_or_404(NotificationTemplate, pk=pk, is_active=True)
    
    data = {
        'id': template.id,
        'name': template.name,
        'notification_type': template.notification_type,
        'sms_body': template.sms_body,
        'email_subject': template.email_subject,
        'email_body': template.email_body,
    }
    
    return JsonResponse(data)


# ✨✨✨ END NEW TEMPLATE VIEWS ✨✨✨


class NotificationLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View to display notification logs
    """
    model = NotificationLog
    template_name = 'notifications/log_list.html'
    context_object_name = 'logs'
    paginate_by = 50
    permission_required = 'notifications.view_notificationlog'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('client', 'appointment', 'sent_by')
        
        # Apply filters
        channel = self.request.GET.get('channel')
        status = self.request.GET.get('status')
        client_id = self.request.GET.get('client')
        
        if channel:
            queryset = queryset.filter(channel=channel)
        if status:
            queryset = queryset.filter(status=status)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['channels'] = NotificationLog.CHANNEL_CHOICES
        context['statuses'] = NotificationLog.STATUS_CHOICES
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_sent'] = queryset.filter(status='sent').count()
        context['total_failed'] = queryset.filter(status='failed').count()
        context['total_pending'] = queryset.filter(status='pending').count()
        
        return context


class NotificationLogDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View to display notification log details
    """
    model = NotificationLog
    template_name = 'notifications/log_detail.html'
    context_object_name = 'log'
    permission_required = 'notifications.view_notificationlog'


class ScheduledNotificationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View to display scheduled notifications
    """
    model = ScheduledNotification
    template_name = 'notifications/scheduled_list.html'
    context_object_name = 'scheduled_notifications'
    paginate_by = 50
    permission_required = 'notifications.view_schedulednotification'
    
    def get_queryset(self):
        return super().get_queryset().select_related('appointment__client', 'appointment__service')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = self.get_queryset()
        context['pending_count'] = queryset.filter(sent=False).count()
        context['sent_count'] = queryset.filter(sent=True).count()
        
        return context


@login_required
def notification_stats_api(request):
    """
    API endpoint for notification statistics (for dashboard widgets)
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Get stats for last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    logs = NotificationLog.objects.filter(created_at__gte=thirty_days_ago)
    
    stats = {
        'total': logs.count(),
        'sent': logs.filter(status='sent').count(),
        'failed': logs.filter(status='failed').count(),
        'sms_count': logs.filter(channel='sms').count(),
        'email_count': logs.filter(channel='email').count(),
        'by_day': {},
    }
    
    # Group by day
    for i in range(30):
        day = (timezone.now() - timedelta(days=i)).date()
        day_logs = logs.filter(created_at__date=day)
        stats['by_day'][str(day)] = {
            'total': day_logs.count(),
            'sent': day_logs.filter(status='sent').count(),
            'failed': day_logs.filter(status='failed').count(),
        }
    
    return JsonResponse(stats)