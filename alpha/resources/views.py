"""
Resources Views - FIXED VERSION
Place this at: alpha/resources/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Room, Machine


# ===== RESOURCES DASHBOARD =====

class ResourcesIndexView(LoginRequiredMixin, TemplateView):
    """Resources dashboard with stats"""
    template_name = 'resources/resources_index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Machine stats
        context['total_machines'] = Machine.objects.count()
        context['active_machines'] = Machine.objects.filter(is_active=True).count()
        # Room stats
        context['total_rooms'] = Room.objects.count()
        context['active_rooms'] = Room.objects.filter(is_active=True).count()
        # Recent items (limit to 5)
        context['recent_machines'] = Machine.objects.all()[:5]
        context['recent_rooms'] = Room.objects.all()[:5]
        return context


# ===== MACHINES =====

class MachineListView(LoginRequiredMixin, ListView):
    """List all machines"""
    model = Machine
    template_name = 'resources/machine_list.html'
    context_object_name = 'machines'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Machine.objects.all()
        
        # Filter by active status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset.order_by('name')


class MachineDetailView(LoginRequiredMixin, DetailView):
    """View a single machine"""
    model = Machine
    template_name = 'resources/machine_detail.html'
    context_object_name = 'machine'


class MachineCreateView(LoginRequiredMixin, CreateView):
    """Create a new machine"""
    model = Machine
    template_name = 'resources/machine_form.html'
    fields = ['name', 'notes', 'is_active']
    
    def get_success_url(self):
        # ✅ FIXED: Removed 'alpha:' prefix
        return reverse_lazy('resources:machine-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Machine created successfully!'))
        return super().form_valid(form)


class MachineUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a machine"""
    model = Machine
    template_name = 'resources/machine_form.html'
    fields = ['name', 'notes', 'is_active']
    
    def get_success_url(self):
        # ✅ FIXED: Removed 'alpha:' prefix
        return reverse_lazy('resources:machine-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Machine updated successfully!'))
        return super().form_valid(form)


class MachineDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a machine"""
    model = Machine
    template_name = 'resources/machine_confirm_delete.html'
    # ✅ FIXED: Removed 'alpha:' prefix
    success_url = reverse_lazy('resources:machine-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Machine deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ===== ROOMS =====

class RoomListView(LoginRequiredMixin, ListView):
    """List all rooms"""
    model = Room
    template_name = 'resources/room_list.html'
    context_object_name = 'rooms'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Room.objects.all()
        
        # Filter by active status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('name')


class RoomDetailView(LoginRequiredMixin, DetailView):
    """View a single room"""
    model = Room
    template_name = 'resources/room_detail.html'
    context_object_name = 'room'


class RoomCreateView(LoginRequiredMixin, CreateView):
    """Create a new room"""
    model = Room
    template_name = 'resources/room_form.html'
    fields = ['name', 'is_active']
    
    def get_success_url(self):
        # ✅ FIXED: Removed 'alpha:' prefix
        return reverse_lazy('resources:room-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Room created successfully!'))
        return super().form_valid(form)


class RoomUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a room"""
    model = Room
    template_name = 'resources/room_form.html'
    fields = ['name', 'is_active']
    
    def get_success_url(self):
        # ✅ FIXED: Removed 'alpha:' prefix
        return reverse_lazy('resources:room-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Room updated successfully!'))
        return super().form_valid(form)


class RoomDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a room"""
    model = Room
    template_name = 'resources/room_confirm_delete.html'
    # ✅ FIXED: Removed 'alpha:' prefix
    success_url = reverse_lazy('resources:room-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Room deleted successfully.'))
        return super().delete(request, *args, **kwargs)