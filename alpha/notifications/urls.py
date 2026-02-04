from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Bulk notifications
    path('bulk-send/', views.bulk_notification_view, name='bulk-send'),
    
    # Notification logs
    path('logs/', views.NotificationLogListView.as_view(), name='logs'),
    path('logs/<int:pk>/', views.NotificationLogDetailView.as_view(), name='log-detail'),
    
    # Scheduled notifications
    path('scheduled/', views.ScheduledNotificationListView.as_view(), name='scheduled'),
    
    # Templates
    path('templates/', views.template_list_view, name='templates'),

    path('templates/create/', views.template_create_view, name='template-create'),
    path('templates/<int:pk>/edit/', views.template_edit_view, name='template-edit'),
    path('templates/<int:pk>/delete/', views.template_delete_view, name='template-delete'),
    path('templates/<int:pk>/api/', views.template_get_api, name='template-api'),  # For AJAX
    
    # API
    path('api/stats/', views.notification_stats_api, name='stats-api'),
]