"""
Visits Views - UPDATED with notification count endpoint
Place this at: alpha/visits/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, F
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Visit


class VisitListView(LoginRequiredMixin, ListView):
    """Display all visits with filtering and search"""
    model = Visit
    template_name = 'visits/visit_list.html'
    context_object_name = 'visits'
    paginate_by = 50
    
    def get_queryset(self):
        """
        Get visits with related data to avoid N+1 queries
        Also handle filtering from URL parameters
        """
        queryset = Visit.objects.select_related(
            'appointment',
            'appointment__client',
            'appointment__service',
            'staff',
            'machine'
        ).all()
        
        # Filter by staff if provided
        staff_id = self.request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by machine if provided
        machine_id = self.request.GET.get('machine')
        if machine_id:
            queryset = queryset.filter(machine_id=machine_id)
        
        # Filter by payment status
        payment_status = self.request.GET.get('payment_status')
        if payment_status == 'paid':
            queryset = queryset.filter(paid_amount__gte=F('charge_amount'))
        elif payment_status == 'partial':
            queryset = queryset.filter(
                paid_amount__gt=0,
                paid_amount__lt=F('charge_amount')
            )
        elif payment_status == 'unpaid':
            queryset = queryset.filter(paid_amount=0)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(appointment__client__full_name__icontains=search) |
                Q(appointment__service__name__icontains=search) |
                Q(area__icontains=search) |
                Q(remarks__icontains=search)
            )
        
        return queryset.order_by('-appointment__start')
    
    def get_context_data(self, **kwargs):
        """Add extra context for the template"""
        context = super().get_context_data(**kwargs)
        
        # Count stats
        context['total_count'] = Visit.objects.count()
        context['unpaid_count'] = Visit.objects.filter(paid_amount=0).count()
        
        # Revenue stats
        revenue_stats = Visit.objects.aggregate(
            total_charged=Sum('charge_amount'),
            total_paid=Sum('paid_amount')
        )
        context['total_revenue'] = revenue_stats['total_paid'] or 0
        context['pending_revenue'] = (
            (revenue_stats['total_charged'] or 0) - 
            (revenue_stats['total_paid'] or 0)
        )
        
        # Pass current filters
        context['current_staff'] = self.request.GET.get('staff', '')
        context['current_machine'] = self.request.GET.get('machine', '')
        context['current_payment_status'] = self.request.GET.get('payment_status', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class VisitDetailView(LoginRequiredMixin, DetailView):
    """View visit details with full treatment record"""
    model = Visit
    template_name = 'visits/visit_detail.html'
    context_object_name = 'visit'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate balance
        context['balance'] = self.object.charge_amount - self.object.paid_amount
        context['is_paid'] = context['balance'] <= 0
        
        # Get client's visit history
        if self.object.appointment.client:
            context['client_visit_count'] = Visit.objects.filter(
                appointment__client=self.object.appointment.client
            ).count()
        
        return context


class VisitUpdateView(LoginRequiredMixin, UpdateView):
    """Edit visit information - treatment parameters and payment"""
    model = Visit
    template_name = 'visits/visit_form.html'
    fields = [
        'area', 'spot_size_mm', 'fluence_j_cm2', 'pulse_count',
        'charge_amount', 'paid_amount', 'payment_method',
        'remarks'
    ]
    
    def get_success_url(self):
        messages.success(self.request, _('Visit updated successfully!'))
        return reverse_lazy('visits:detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate balance for display
        if self.object:
            context['balance'] = self.object.charge_amount - self.object.paid_amount
        return context


class VisitDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a visit"""
    model = Visit
    template_name = 'visits/visit_confirm_delete.html'
    success_url = reverse_lazy('visits:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Visit deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ✅ NEW: Get incomplete visits count via AJAX
@require_http_methods(["GET"])
def get_incomplete_visits_count(request):
    """
    Return count of incomplete visits as JSON
    Used for dynamically updating notification bell
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': True,
            'count': 0,
            'visits': []
        })
    
    try:
        # Get recent visits and check which are incomplete
        recent_visits = Visit.objects.select_related(
            'appointment',
            'appointment__client',
            'appointment__service',
            'staff'
        ).order_by('-created_at')[:50]
        
        # Filter incomplete visits using the is_complete property
        incomplete_list = [v for v in recent_visits if not v.is_complete]
        
        # Limit to 10 for the dropdown
        incomplete_list = incomplete_list[:10]
        
        # Build JSON response with visit details
        visits_data = []
        for visit in incomplete_list:
            visits_data.append({
                'id': visit.id,
                'client_name': visit.appointment.client.full_name,
                'service_name': visit.appointment.service.name,
                'area': visit.area or '',
                'missing_fields': visit.get_missing_fields(),
                'time_since': visit.time_since_creation(),
                'edit_url': f'/visits/{visit.id}/edit/'  # Adjust URL pattern as needed
            })
        
        return JsonResponse({
            'success': True,
            'count': len(incomplete_list),
            'visits': visits_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'count': 0,
            'visits': []
        }, status=500)