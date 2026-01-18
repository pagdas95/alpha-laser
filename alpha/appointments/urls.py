from django.urls import path
from . import views
from .calendar_views import (
    CalendarView,
    get_appointments_json,
    create_appointment_ajax,
    update_appointment_ajax,
    delete_appointment_ajax
)
from .views import (
    RoomCalendarView,
    get_room_appointments_json, 
    update_appointment_ajax,
    delete_appointment_ajax,
)

app_name = 'appointments'

urlpatterns = [
    # List and create
    path('', views.AppointmentListView.as_view(), name='list'),
    path('create/', views.AppointmentCreateView.as_view(), name='create'),
    
    # Detail, update, delete
    path('<int:pk>/', views.AppointmentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.AppointmentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.AppointmentDeleteView.as_view(), name='delete'),
    
    # Status change
    path('<int:pk>/change-status/', views.AppointmentChangeStatusView.as_view(), name='change-status'),
    
  # ===== ROOM CALENDAR URLS - ADD THESE =====
    path('room-calendar/', RoomCalendarView.as_view(), name='room-calendar'),
    path('api/room-appointments/', get_room_appointments_json, name='room-appointments-json'),
    path('api/appointments/<int:appointment_id>/update/', update_appointment_ajax, name='appointment-update-ajax'),
    path('api/appointments/<int:appointment_id>/delete/', delete_appointment_ajax, name='appointment-delete-ajax'),
    # Calendar URLs
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('api/appointments/', get_appointments_json, name='appointments-json'),
    path('api/appointments/create/', create_appointment_ajax, name='appointment-create-ajax'),
    path('api/appointments/<int:appointment_id>/update/', update_appointment_ajax, name='appointment-update-ajax'),
    path('api/appointments/<int:appointment_id>/delete/', delete_appointment_ajax, name='appointment-delete-ajax'),

    # ✅ NEW: AJAX endpoints
    path('api/service/<int:service_id>/', views.get_service_details, name='service_details'),

    path('api/check-availability/', views.check_room_availability, name='check_availability'),

]