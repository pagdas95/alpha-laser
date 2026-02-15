# alpha/staff/views.py - ADD THIS VIEW
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta

from alpha.users.models import User
from .models import StaffProfile, DayOff
from .forms import DayOffForm, StaffProfileForm


class StaffListView(LoginRequiredMixin, ListView):
    """Display all staff members in a grid layout"""
    model = User
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_members'
    
    def get_queryset(self):
        """Get all users who are staff"""
        queryset = User.objects.filter(
            Q(is_staff=True) | Q(staff_profile__isnull=False)
        ).select_related('staff_profile').distinct()
        
        # Filter by active status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(staff_profile__is_active_staff=True)
        elif status == 'inactive':
            queryset = queryset.filter(staff_profile__is_active_staff=False)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('name', 'username')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_staff'] = self.get_queryset().count()
        context['active_staff'] = User.objects.filter(staff_profile__is_active_staff=True).count()
        return context


class StaffDetailView(LoginRequiredMixin, DetailView):
    """Display staff profile with day-offs and leave balance"""
    model = User
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff_member'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create staff profile
        staff_profile, created = StaffProfile.objects.get_or_create(
            user=self.object
        )
        context['staff_profile'] = staff_profile
        
        # Get day-offs
        today = timezone.now().date()
        
        # Upcoming day-offs
        context['upcoming_dayoffs'] = DayOff.objects.filter(
            staff=self.object,
            start_date__gte=today
        ).order_by('start_date')[:5]
        
        # Current day-off (if any)
        context['current_dayoff'] = DayOff.objects.filter(
            staff=self.object,
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        # Recent past day-offs
        context['past_dayoffs'] = DayOff.objects.filter(
            staff=self.object,
            end_date__lt=today
        ).order_by('-end_date')[:5]
        
        # Statistics
        context['total_dayoffs'] = DayOff.objects.filter(staff=self.object).count()
        context['pending_dayoffs'] = DayOff.objects.filter(staff=self.object, status='pending').count()
        
        # Leave Balance Calculations - 3 SEPARATE TYPES
        current_year = today.year
        
        # Regular Leave Balance (includes half days)
        context['leave_balance'] = staff_profile.get_leave_balance(current_year, 'leave')
        context['leave_used'] = staff_profile.get_leave_used(current_year, 'leave')
        context['leave_allowance'] = float(staff_profile.annual_leave_allowance)
        
        # Sick Leave Balance
        context['sick_balance'] = staff_profile.get_leave_balance(current_year, 'sick')
        context['sick_used'] = staff_profile.get_leave_used(current_year, 'sick')
        context['sick_allowance'] = float(staff_profile.sick_leave_allowance)
        
        # Other/Compensation Balance
        context['other_balance'] = staff_profile.get_leave_balance(current_year, 'other')
        context['other_total'] = staff_profile.get_leave_used(current_year, 'other')  # Total added
        
        return context


class StaffProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update staff profile information"""
    model = StaffProfile
    form_class = StaffProfileForm
    template_name = 'staff/staff_profile_form.html'
    success_message = _("Staff profile updated successfully!")
    
    def get_object(self):
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        profile, created = StaffProfile.objects.get_or_create(user=user)
        return profile
    
    def get_success_url(self):
        return reverse('staff:detail', kwargs={'username': self.object.user.username})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff_member'] = self.object.user
        return context


class DayOffCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create a new day-off request"""
    model = DayOff
    form_class = DayOffForm
    template_name = 'staff/dayoff_form.html'
    success_message = _("Day off request submitted successfully!")
    
    def get_initial(self):
        """Pre-fill staff if viewing own profile"""
        initial = super().get_initial()
        username = self.kwargs.get('username')
        if username:
            user = get_object_or_404(User, username=username)
            initial['staff'] = user
        return initial
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        username = self.kwargs.get('username')
        if username:
            kwargs['staff_user'] = get_object_or_404(User, username=username)
        return kwargs
    
    def form_valid(self, form):
        """Set status to pending by default"""
        dayoff = form.save(commit=False)
        # Always set status to pending for new requests
        if not dayoff.pk:  # New object
            dayoff.status = 'pending'
        dayoff.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to staff profile after creating day-off"""
        username = self.kwargs.get('username') or self.object.staff.username
        return reverse('staff:detail', kwargs={'username': username})


class DayOffListView(LoginRequiredMixin, ListView):
    """List all day-offs for a staff member"""
    model = DayOff
    template_name = 'staff/dayoff_list.html'
    context_object_name = 'dayoffs'
    paginate_by = 20
    
    def get_queryset(self):
        username = self.kwargs.get('username')
        self.staff_user = get_object_or_404(User, username=username)
        
        queryset = DayOff.objects.filter(staff=self.staff_user)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by type
        dayoff_type = self.request.GET.get('type')
        if dayoff_type:
            queryset = queryset.filter(type=dayoff_type)
        
        return queryset.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff_member'] = self.staff_user
        context['staff_profile'] = getattr(self.staff_user, 'staff_profile', None)
        
        # Statistics
        context['total_dayoffs'] = DayOff.objects.filter(staff=self.staff_user).count()
        context['pending_count'] = DayOff.objects.filter(staff=self.staff_user, status='pending').count()
        context['approved_count'] = DayOff.objects.filter(staff=self.staff_user, status='approved').count()
        
        return context


class AllLeavesView(LoginRequiredMixin, ListView):
    """View all leaves for all staff members"""
    model = DayOff
    template_name = 'staff/all_leaves.html'
    context_object_name = 'dayoffs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = DayOff.objects.select_related('staff', 'staff__staff_profile', 'approved_by').all()
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by type
        leave_type = self.request.GET.get('type')
        if leave_type:
            queryset = queryset.filter(type=leave_type)
        
        # Filter by staff
        staff_id = self.request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)
        
        return queryset.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all staff for filter dropdown
        context['all_staff'] = User.objects.filter(
            Q(is_staff=True) | Q(staff_profile__isnull=False)
        ).distinct().order_by('name', 'username')
        
        # Statistics
        context['total_leaves'] = DayOff.objects.count()
        context['pending_count'] = DayOff.objects.filter(status='pending').count()
        context['approved_count'] = DayOff.objects.filter(status='approved').count()
        context['active_leaves'] = DayOff.objects.filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
            status='approved'
        ).count()
        
        return context


class DayOffUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update a day-off request"""
    model = DayOff
    form_class = DayOffForm
    template_name = 'staff/dayoff_form.html'
    success_message = _("Day off updated successfully!")
    
    def get_success_url(self):
        return reverse('staff:dayoff-list', kwargs={'username': self.object.staff.username})


class DayOffDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete a day-off request"""
    model = DayOff
    template_name = 'staff/dayoff_confirm_delete.html'
    success_message = _("Day off deleted successfully!")
    
    def get_success_url(self):
        return reverse('staff:dayoff-list', kwargs={'username': self.object.staff.username})


# Quick action views for day-off approval
class DayOffApproveView(LoginRequiredMixin, DetailView):
    """Approve a day-off request"""
    model = DayOff
    
    def get(self, request, *args, **kwargs):
        dayoff = self.get_object()
        dayoff.approve(request.user)
        messages.success(request, _('Day off approved successfully!'))
        return redirect('staff:dayoff-list', username=dayoff.staff.username)


class DayOffRejectView(LoginRequiredMixin, DetailView):
    """Reject a day-off request"""
    model = DayOff
    
    def get(self, request, *args, **kwargs):
        dayoff = self.get_object()
        dayoff.reject(request.user)
        messages.warning(request, _('Day off rejected.'))
        return redirect('staff:dayoff-list', username=dayoff.staff.username)