"""
Room-Based Calendar Views (Updated for your Appointment model)
Add these to your appointments/views.py or create appointments/room_calendar_views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from datetime import datetime, date
from .models import Appointment
from alpha.resources.models import Room
import json


class RoomCalendarView(LoginRequiredMixin, TemplateView):
    """Calendar view showing appointments by room"""
    template_name = 'appointments/room_calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all active rooms
        context['rooms'] = Room.objects.filter(is_active=True).order_by('name')
        
        # Today's stats
        today = date.today()
        context['todays_total'] = Appointment.objects.filter(
            start__date=today
        ).count()
        
        return context


@require_http_methods(["GET"])
def get_room_appointments_json(request):
    """
    Return appointments filtered by room as JSON for FullCalendar
    """
    # Get filters from request
    start = request.GET.get('start')
    end = request.GET.get('end')
    room_id = request.GET.get('room_id')
    
    # Build query
    appointments = Appointment.objects.select_related(
        'client', 'service', 'room', 'staff'
    ).all()
    
    # Filter by room
    if room_id:
        appointments = appointments.filter(room_id=room_id)
    
    # Filter by date range
    if start:
        appointments = appointments.filter(start__gte=start)
    if end:
        appointments = appointments.filter(end__lte=end)
    
    # Convert to FullCalendar format
    events = []
    for apt in appointments:
        # Map your status to colors
        color_map = {
            'booked': 'bg-primary',      # Κλεισμένο - Blue
            'completed': 'bg-success',   # Ολοκληρώθηκε - Green
            'no_show': 'bg-warning',     # Δεν προσήλθε - Yellow
            'cancelled': 'bg-danger',    # Ακυρώθηκε - Red
        }
        
        # Get client name
        client_name = str(apt.client)  # Uses Client's __str__ method
        
        event = {
            'id': apt.id,
            'title': f"{client_name} - {apt.service.name}",
            'start': apt.start.isoformat(),
            'end': apt.end.isoformat(),
            'className': color_map.get(apt.status, 'bg-primary'),
            'extendedProps': {
                'appointmentId': apt.id,
                'clientId': apt.client.id,
                'clientName': client_name,
                'serviceName': apt.service.name,
                'roomId': apt.room.id,
                'roomName': apt.room.name,
                'staffName': apt.staff.get_full_name() if hasattr(apt.staff, 'get_full_name') else str(apt.staff),
                'machineName': apt.machine.name if apt.machine else '',
                'status': apt.status,
                'statusDisplay': apt.get_status_display(),
                'notes': apt.notes or '',
            }
        }
        events.append(event)
    
    return JsonResponse(events, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def update_appointment_ajax(request, appointment_id):
    """
    Update appointment via AJAX from calendar (drag & drop)
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        data = json.loads(request.body)
        
        # Update start/end datetime if changed
        if 'start' in data:
            new_start = parse_datetime(data['start'])
            if new_start:
                # Calculate duration
                duration = appointment.end - appointment.start
                appointment.start = new_start
                appointment.end = new_start + duration
        
        # Update room if changed (when dragging between calendars)
        if 'room_id' in data:
            appointment.room_id = data['room_id']
        
        appointment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Appointment updated successfully'
        })
        
    except Appointment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Appointment not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_appointment_ajax(request, appointment_id):
    """
    Delete appointment via AJAX from calendar
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Appointment deleted successfully'
        })
        
    except Appointment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Appointment not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)