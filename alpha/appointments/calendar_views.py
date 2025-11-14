"""
Calendar Views for Appointments
Add these to your appointments/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from .models import Appointment
import json


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendar page view"""
    template_name = 'appointments/calendar.html'


@require_http_methods(["GET"])
def get_appointments_json(request):
    """
    Return appointments as JSON for FullCalendar
    """
    # Get date range from request (optional)
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    # Build query
    appointments = Appointment.objects.all()
    
    if start:
        appointments = appointments.filter(date__gte=start)
    if end:
        appointments = appointments.filter(date__lte=end)
    
    # Convert to FullCalendar format
    events = []
    for apt in appointments:
        # Combine date and time for start
        start_datetime = datetime.combine(apt.date, apt.time)
        
        # Calculate end time (add duration)
        if apt.duration:
            end_datetime = start_datetime + timedelta(minutes=apt.duration)
        else:
            end_datetime = start_datetime + timedelta(hours=1)  # Default 1 hour
        
        # Determine color based on status
        color_map = {
            'scheduled': 'bg-primary',
            'confirmed': 'bg-success',
            'completed': 'bg-info',
            'cancelled': 'bg-danger',
            'no_show': 'bg-warning',
        }
        
        event = {
            'id': apt.id,
            'title': f"{apt.client.full_name} - {apt.service.name if apt.service else 'No Service'}",
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat(),
            'className': color_map.get(apt.status, 'bg-primary'),
            'extendedProps': {
                'clientId': apt.client.id,
                'clientName': apt.client.full_name,
                'serviceName': apt.service.name if apt.service else '',
                'status': apt.status,
                'notes': apt.notes or '',
            }
        }
        events.append(event)
    
    return JsonResponse(events, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def create_appointment_ajax(request):
    """
    Create appointment via AJAX from calendar
    """
    try:
        data = json.loads(request.body)
        
        # Parse the datetime
        start_datetime = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        
        # Create appointment
        appointment = Appointment.objects.create(
            client_id=data['clientId'],
            service_id=data.get('serviceId'),
            date=start_datetime.date(),
            time=start_datetime.time(),
            status='scheduled',
            notes=data.get('notes', '')
        )
        
        return JsonResponse({
            'success': True,
            'id': appointment.id,
            'message': 'Appointment created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def update_appointment_ajax(request, appointment_id):
    """
    Update appointment via AJAX from calendar
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        data = json.loads(request.body)
        
        # Update datetime if changed
        if 'start' in data:
            start_datetime = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
            appointment.date = start_datetime.date()
            appointment.time = start_datetime.time()
        
        # Update other fields if provided
        if 'clientId' in data:
            appointment.client_id = data['clientId']
        if 'serviceId' in data:
            appointment.service_id = data['serviceId']
        if 'status' in data:
            appointment.status = data['status']
        if 'notes' in data:
            appointment.notes = data['notes']
        
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