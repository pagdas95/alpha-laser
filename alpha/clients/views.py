from django.shortcuts import render

# Create your views here.
"""
Clients Views
Place this at: alpha/clients/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Client


class ClientListView(LoginRequiredMixin, ListView):
    """Display all clients with filtering and search"""
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 50
    
    def get_queryset(self):
        """
        Get clients with appointment counts to avoid N+1 queries
        Also handle filtering and search from URL parameters
        """
        queryset = Client.objects.annotate(
            appointment_count=Count('appointments'),
            visit_count=Count('appointments__visit')
        ).all()
        
        # Filter by skin type if provided
        skin_type = self.request.GET.get('skin_type')
        if skin_type:
            queryset = queryset.filter(skin_type=skin_type)
        
        # Filter by hair color if provided
        hair_color = self.request.GET.get('hair_color')
        if hair_color:
            queryset = queryset.filter(hair_color=hair_color)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add extra context for the template"""
        context = super().get_context_data(**kwargs)
        
        # Count stats
        context['total_count'] = Client.objects.count()
        context['with_email_count'] = Client.objects.exclude(email='').count()
        
        # Pass current filters
        context['current_skin_type'] = self.request.GET.get('skin_type', '')
        context['current_hair_color'] = self.request.GET.get('hair_color', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        # Choices for filter dropdowns
        context['skin_type_choices'] = Client.SKIN_TYPE_CHOICES
        context['hair_color_choices'] = Client.HAIR_COLOR_CHOICES
        
        return context


class ClientCreateView(LoginRequiredMixin, CreateView):
    """Create a new client"""
    model = Client
    template_name = 'clients/client_form.html'
    fields = ['full_name', 'phone', 'email', 'birth_date', 'skin_type', 'hair_color', 'notes']
    success_url = reverse_lazy('clients:list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Client created successfully!'))
        return super().form_valid(form)


class ClientDetailView(LoginRequiredMixin, DetailView):
    """View client details with appointment history"""
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get appointments for this client
        appointments = self.object.appointments.select_related(
            'service', 'staff', 'room', 'machine'
        ).order_by('-start')[:10]  # Last 10 appointments
        
        context['recent_appointments'] = appointments
        context['total_appointments'] = self.object.appointments.count()
        context['completed_visits'] = self.object.appointments.filter(status='completed').count()
        
        # Get consents
        context['consents'] = self.object.consents.all().order_by('-accepted_at')
        
        return context


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    """Edit client information"""
    model = Client
    template_name = 'clients/client_form.html'
    fields = ['full_name', 'phone', 'email', 'birth_date', 'skin_type', 'hair_color', 'notes']
    
    def get_success_url(self):
        messages.success(self.request, _('Client updated successfully!'))
        return reverse_lazy('clients:detail', kwargs={'pk': self.object.pk})


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a client"""
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    success_url = reverse_lazy('clients:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Client deleted successfully.'))
        return super().delete(request, *args, **kwargs)