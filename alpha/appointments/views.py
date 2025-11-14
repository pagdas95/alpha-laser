"""
Appointments Views
Place this at: alpha/appointments/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Appointment
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from datetime import datetime, date
import json

class AppointmentListView(LoginRequiredMixin, ListView):
    """Display all appointments with filtering and search"""
    model = Appointment
    template_name = 'appointments/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 50  # For pagination if needed
    
    def get_queryset(self):
        """
        Get appointments with related data to avoid N+1 queries
        Also handle filtering from URL parameters
        """
        queryset = Appointment.objects.select_related(
            'client',
            'service', 
            'staff',
            'room',
            'machine'
        ).all()
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by staff if provided
        staff_id = self.request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(service__name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add extra context for the template"""
        context = super().get_context_data(**kwargs)
        
        # Count by status for display
        context['total_count'] = Appointment.objects.count()
        context['booked_count'] = Appointment.objects.filter(status='booked').count()
        context['completed_count'] = Appointment.objects.filter(status='completed').count()
        
        # Pass current filters
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        # Status choices for filter dropdown
        context['status_choices'] = Appointment.STATUS_CHOICES
        
        return context


class AppointmentChangeStatusView(LoginRequiredMixin, View):
    """Handle status changes for appointments"""
    
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        new_status = request.POST.get('status')
        
        if new_status in dict(Appointment.STATUS_CHOICES):
            old_status = appointment.status
            appointment.status = new_status
            appointment.save()
            
            # Success messages based on status
            status_messages = {
                'completed': _('Appointment marked as completed. Visit record created.'),
                'no_show': _('Appointment marked as No Show.'),
                'cancelled': _('Appointment cancelled.'),
                'booked': _('Appointment reopened.'),
            }
            
            messages.success(request, status_messages.get(new_status, _('Status updated.')))
        else:
            messages.error(request, _('Invalid status.'))
        
        return redirect('appointments:list')


class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    template_name = 'appointments/appointment_form.html'
    fields = ['client', 'service', 'staff', 'room', 'machine', 'start', 'end', 'notes', 'price_override']
    success_url = reverse_lazy('appointments:list')
    
    def get_initial(self):
        """Pre-fill client if provided in URL parameter"""
        initial = super().get_initial()
        client_id = self.request.GET.get('client')
        if client_id:
            try:
                # Just set the ID, Django will handle the validation
                initial['client'] = client_id
            except ValueError:
                pass
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, _('Appointment created successfully!'))
        return super().form_valid(form)


class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if visit exists
        context['has_visit'] = hasattr(self.object, 'visit')
        if context['has_visit']:
            context['visit'] = self.object.visit
        return context


class AppointmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Appointment
    template_name = 'appointments/appointment_form.html'
    fields = ['client', 'service', 'staff', 'room', 'machine', 'start', 'end', 'status', 'notes', 'price_override']
    
    def get_success_url(self):
        messages.success(self.request, _('Appointment updated successfully!'))
        return reverse_lazy('appointments:detail', kwargs={'pk': self.object.pk})


class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Appointment
    template_name = 'appointments/appointment_confirm_delete.html'
    success_url = reverse_lazy('appointments:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Appointment deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class AppointmentCalendarView(LoginRequiredMixin, ListView):
    """Calendar view - placeholder for now"""
    model = Appointment
    template_name = 'appointments/calendar.html'

class RoomCalendarView(LoginRequiredMixin, TemplateView):
    """Calendar view showing appointments by room"""
    template_name = 'appointments/room_calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from alpha.resources.models import Room
        
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
        client_name = str(apt.client)
        
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