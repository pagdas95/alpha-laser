# alpha/staff/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import StaffProfile, DayOff


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'position', 
        'employment_type', 
        'hire_date', 
        'annual_leave_allowance',
        'sick_leave_allowance',
        'leave_balance_display',
        'sick_balance_display',
        'compensation_balance_display',
        'is_active_staff', 
        'can_be_booked'
    ]
    list_filter = ['employment_type', 'is_active_staff', 'can_be_booked', 'hire_date']
    search_fields = ['user__name', 'user__username', 'user__email', 'position', 'employee_id', 'phone']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at', 'years_of_service', 
                       'leave_balance_display', 'sick_balance_display', 'compensation_balance_display',
                       'leave_used_this_year', 'sick_used_this_year', 'compensation_total']
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Professional Information'), {
            'fields': ('position', 'employment_type', 'hire_date', 'employee_id')
        }),
        (_('Contact Information'), {
            'fields': ('phone', 'emergency_contact', 'emergency_phone')
        }),
        (_('Professional Details'), {
            'fields': ('certifications', 'specializations', 'bio'),
            'classes': ('collapse',)
        }),
        (_('Leave Management - 3 Separate Types'), {
            'fields': (
                ('annual_leave_allowance', 'leave_balance_display', 'leave_used_this_year'),
                ('sick_leave_allowance', 'sick_balance_display', 'sick_used_this_year'),
                ('other_balance', 'compensation_balance_display', 'compensation_total'),
            ),
            'description': 'Leave allowances and balances for 3 separate leave types'
        }),
        (_('Settings'), {
            'fields': ('avatar', 'is_active_staff', 'can_be_booked')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'years_of_service'),
            'classes': ('collapse',)
        }),
    )
    
    def leave_balance_display(self, obj):
        """Display annual leave balance with color coding"""
        balance = obj.get_leave_balance(leave_type='leave')
        if balance < 5:
            color = 'red'
        elif balance < 10:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>',
            color,
            balance
        )
    leave_balance_display.short_description = _('Leave Balance')
    
    def sick_balance_display(self, obj):
        """Display sick leave balance with color coding"""
        balance = obj.get_leave_balance(leave_type='sick')
        if balance < 2:
            color = 'red'
        elif balance < 5:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>',
            color,
            balance
        )
    sick_balance_display.short_description = _('Sick Balance')
    
    def compensation_balance_display(self, obj):
        """Display compensation balance"""
        balance = obj.get_leave_balance(leave_type='other')
        return format_html(
            '<span style="color: blue; font-weight: bold;">{} days</span>',
            balance
        )
    compensation_balance_display.short_description = _('Compensation')
    
    def leave_used_this_year(self, obj):
        """Display leave used this year"""
        used = obj.get_leave_used(leave_type='leave')
        return f"{used} days"
    leave_used_this_year.short_description = _('Leave Used')
    
    def sick_used_this_year(self, obj):
        """Display sick leave used this year"""
        used = obj.get_leave_used(leave_type='sick')
        return f"{used} days"
    sick_used_this_year.short_description = _('Sick Used')
    
    def compensation_total(self, obj):
        """Display total compensation added"""
        total = obj.get_leave_used(leave_type='other')
        return f"+{total} days"
    compensation_total.short_description = _('Comp. Added')
    
    def years_of_service(self, obj):
        """Display years of service"""
        years = obj.years_of_service
        return f"{years} years" if years != 1 else "1 year"
    years_of_service.short_description = _('Years of Service')


@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = [
        'staff_name',
        'type',
        'start_date',
        'end_date',
        'duration_days',
        'leave_deduction_display',
        'status_badge',
        'approved_by',
        'created_at'
    ]
    list_filter = [
        'status', 
        'type', 
        'start_date', 
        'created_at',
        ('approved_by', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'staff__name', 
        'staff__username', 
        'staff__email',
        'reason', 
        'approval_notes'
    ]
    date_hierarchy = 'start_date'
    raw_id_fields = ['staff', 'approved_by']
    readonly_fields = [
        'duration_days_display', 
        'leave_deduction_display', 
        'is_active',
        'is_upcoming',
        'is_past',
        'created_at', 
        'updated_at'
    ]
    
    fieldsets = (
        (_('Staff Member'), {
            'fields': ('staff',)
        }),
        (_('Date Range'), {
            'fields': ('start_date', 'end_date', 'duration_days_display')
        }),
        (_('Leave Details'), {
            'fields': ('type', 'reason', 'leave_deduction_display')
        }),
        (_('Status'), {
            'fields': ('status', 'is_active', 'is_upcoming', 'is_past')
        }),
        (_('Approval'), {
            'fields': ('approved_by', 'approval_date', 'approval_notes')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_selected', 'reject_selected', 'mark_as_pending']
    
    def staff_name(self, obj):
        """Display staff name with link to profile"""
        return obj.staff.name or obj.staff.username
    staff_name.short_description = _('Staff')
    staff_name.admin_order_field = 'staff__name'
    
    def duration_days_display(self, obj):
        """Display duration in days"""
        days = obj.duration_days
        return f"{days} day{'s' if days != 1 else ''}"
    duration_days_display.short_description = _('Duration')
    
    def leave_deduction_display(self, obj):
        """Display leave deduction with color and explanation"""
        deduction = obj.leave_deduction
        
        if deduction > 0:
            color = 'green'
            icon = '+'
            explanation = 'Added to balance'
        else:
            color = 'red'
            icon = ''
            explanation = 'Deducted from balance'
        
        # Add explanation based on type
        if obj.type == 'half_day':
            type_note = '(Always -0.5 for half day)'
        elif obj.type == 'other':
            type_note = '(Always +1 for compensation)'
        elif obj.type in ['leave', 'sick']:
            type_note = f'({obj.duration_days} days × -1)'
        else:
            type_note = ''
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{} days</span><br>'
            '<small style="color: gray;">{} {}</small>',
            color,
            icon,
            deduction,
            explanation,
            type_note
        )
    leave_deduction_display.short_description = _('Leave Deduction')
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'pending': '#FFA500',  # Orange
            'approved': '#28a745',  # Green
            'rejected': '#dc3545',  # Red
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def is_active(self, obj):
        """Show if currently on leave"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Currently Active</span>')
        return format_html('<span style="color: gray;">—</span>')
    is_active.short_description = _('Active Now?')
    is_active.boolean = True
    
    def is_upcoming(self, obj):
        """Show if leave is upcoming"""
        if obj.is_upcoming:
            return format_html('<span style="color: blue;">✓ Upcoming</span>')
        return format_html('<span style="color: gray;">—</span>')
    is_upcoming.short_description = _('Upcoming?')
    
    def is_past(self, obj):
        """Show if leave has passed"""
        if obj.is_past:
            return format_html('<span style="color: gray;">✓ Past</span>')
        return format_html('<span style="color: gray;">—</span>')
    is_past.short_description = _('Past?')
    
    # Bulk Actions
    def approve_selected(self, request, queryset):
        """Bulk approve day-off requests"""
        updated = 0
        for dayoff in queryset.filter(status='pending'):
            dayoff.approve(request.user)
            updated += 1
        
        self.message_user(
            request,
            _(f'{updated} day-off request(s) approved successfully.')
        )
    approve_selected.short_description = _("✓ Approve selected day-off requests")
    
    def reject_selected(self, request, queryset):
        """Bulk reject day-off requests"""
        updated = 0
        for dayoff in queryset.filter(status='pending'):
            dayoff.reject(request.user, "Bulk rejection from admin")
            updated += 1
        
        self.message_user(
            request,
            _(f'{updated} day-off request(s) rejected.')
        )
    reject_selected.short_description = _("✗ Reject selected day-off requests")
    
    def mark_as_pending(self, request, queryset):
        """Mark as pending"""
        updated = queryset.update(status='pending', approved_by=None, approval_date=None)
        self.message_user(
            request,
            _(f'{updated} day-off request(s) marked as pending.')
        )
    mark_as_pending.short_description = _("⟲ Mark as pending")
    
    # Custom queryset for better performance
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('staff', 'approved_by', 'staff__staff_profile')


# Optional: Inline admin to show day-offs on User admin page
class DayOffInline(admin.TabularInline):
    model = DayOff
    extra = 0
    fields = ['start_date', 'end_date', 'type', 'status', 'leave_deduction_display']
    readonly_fields = ['leave_deduction_display']
    can_delete = False
    
    def leave_deduction_display(self, obj):
        """Display leave deduction"""
        deduction = obj.leave_deduction
        if deduction > 0:
            return f"+{deduction} days"
        return f"{deduction} days"
    leave_deduction_display.short_description = 'Deduction'
    
    def has_add_permission(self, request, obj=None):
        return False


# You can add this inline to your User admin if you want
# from alpha.users.admin import UserAdmin
# UserAdmin.inlines = [DayOffInline]