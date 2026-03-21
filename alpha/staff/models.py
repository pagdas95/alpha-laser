# alpha/staff/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import datetime


class StaffProfile(models.Model):
    """Extended profile information for staff members"""
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    
    # Professional Information - Position is now FREE TEXT
    position = models.CharField(
        _("Position"),
        max_length=100,
        blank=True,
        help_text=_("e.g., Laser Technician, Senior Nurse, Receptionist")
    )
    employment_type = models.CharField(
        _("Employment Type"),
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='full_time'
    )
    hire_date = models.DateField(_("Hire Date"), null=True, blank=True)
    employee_id = models.CharField(_("Employee ID"), max_length=20, blank=True)
    
    # ✨✨✨ NEW: WORKING SCHEDULE FOR PART-TIME STAFF ✨✨✨
    working_schedule = models.JSONField(
        _("Working Schedule"),
        default=dict,
        blank=True,
        help_text=_("Weekly working schedule with days and hours")
    )
    # Format: {
    #     "monday": {"working": true, "start": "09:00", "end": "17:00"},
    #     "tuesday": {"working": true, "start": "09:00", "end": "17:00"},
    #     ...
    # }
    
    # Contact Information
    phone = models.CharField(_("Phone"), max_length=20, blank=True)
    emergency_contact = models.CharField(_("Emergency Contact"), max_length=100, blank=True)
    emergency_phone = models.CharField(_("Emergency Phone"), max_length=20, blank=True)
    
    # Professional Details
    certifications = models.TextField(_("Certifications"), blank=True, help_text="List any relevant certifications")
    specializations = models.TextField(_("Specializations"), blank=True)
    bio = models.TextField(_("Bio"), blank=True)
    
    # Profile Picture
    avatar = models.ImageField(_("Avatar"), upload_to='staff/avatars/', null=True, blank=True)
    
    # Leave Allowances - 3 SEPARATE TYPES
    annual_leave_allowance = models.DecimalField(
        _("Annual Leave Allowance (Days)"),
        max_digits=5,
        decimal_places=1,
        default=21.0,
        help_text=_("Regular leave days allowed per year (includes half days)")
    )
    
    sick_leave_allowance = models.DecimalField(
        _("Sick Leave Allowance (Days)"),
        max_digits=5,
        decimal_places=1,
        default=10.0,
        help_text=_("Sick leave days allowed per year")
    )
    
    other_balance = models.DecimalField(
        _("Other/Compensation Balance (Days)"),
        max_digits=5,
        decimal_places=1,
        default=0.0,
        help_text=_("Accumulated compensation/bonus days (starts at 0, increases with Other entries)")
    )
    
    # Settings
    is_active_staff = models.BooleanField(_("Active Staff"), default=True)
    can_be_booked = models.BooleanField(_("Can Be Booked"), default=True, help_text="Can clients book appointments with this staff member?")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Staff Profile")
        verbose_name_plural = _("Staff Profiles")
        ordering = ['user__name']
    
    def __str__(self):
        return f"{self.user.name or self.user.username} - {self.position or 'Staff'}"
    
    @property
    def full_name(self):
        """Get staff member's full name"""
        return self.user.name or self.user.username
    
    @property
    def years_of_service(self):
        """Calculate years of service"""
        if self.hire_date:
            delta = timezone.now().date() - self.hire_date
            return delta.days // 365
        return 0
    
    # ✨✨✨ NEW: WORKING SCHEDULE HELPER METHODS ✨✨✨
    
    def get_working_schedule(self):
        """Get working schedule with default structure"""
        default_schedule = {
            'monday': {'working': False, 'start': '09:00', 'end': '17:00'},
            'tuesday': {'working': False, 'start': '09:00', 'end': '17:00'},
            'wednesday': {'working': False, 'start': '09:00', 'end': '17:00'},
            'thursday': {'working': False, 'start': '09:00', 'end': '17:00'},
            'friday': {'working': False, 'start': '09:00', 'end': '17:00'},
            'saturday': {'working': False, 'start': '09:00', 'end': '17:00'},
            'sunday': {'working': False, 'start': '09:00', 'end': '17:00'},
        }
        
        # Merge with saved schedule
        if self.working_schedule:
            for day, data in self.working_schedule.items():
                if day in default_schedule:
                    default_schedule[day].update(data)
        
        return default_schedule
    
    def get_working_days(self):
        """Get list of days the staff member works"""
        schedule = self.get_working_schedule()
        working_days = [
            day.capitalize() for day, data in schedule.items()
            if data.get('working', False)
        ]
        return working_days
    
    def get_total_weekly_hours(self):
        """Calculate total working hours per week"""
        schedule = self.get_working_schedule()
        total_hours = 0
        
        for day, data in schedule.items():
            if data.get('working', False):
                try:
                    start = datetime.strptime(data['start'], '%H:%M')
                    end = datetime.strptime(data['end'], '%H:%M')
                    hours = (end - start).seconds / 3600
                    total_hours += hours
                except (ValueError, KeyError):
                    pass
        
        return round(total_hours, 1)
    
    def is_working_on(self, day_name):
        """Check if staff is working on a specific day (e.g., 'monday')"""
        schedule = self.get_working_schedule()
        day_data = schedule.get(day_name.lower(), {})
        return day_data.get('working', False)
    
    def get_working_hours_for_day(self, day_name):
        """Get working hours for a specific day"""
        schedule = self.get_working_schedule()
        day_data = schedule.get(day_name.lower(), {})
        
        if day_data.get('working', False):
            return {
                'start': day_data.get('start', '09:00'),
                'end': day_data.get('end', '17:00')
            }
        return None
    
    # ... (keep all the existing leave balance methods) ...
    
    def get_leave_balance(self, year=None, leave_type='leave'):
        """Calculate remaining leave balance for the year by type"""
        if year is None:
            year = timezone.now().year
        
        # Get all approved day-offs for this year of this type
        year_start = datetime(year, 1, 1).date()
        year_end = datetime(year, 12, 31).date()
        
        dayoffs = DayOff.objects.filter(
            staff=self.user,
            status='approved',
            start_date__gte=year_start,
            start_date__lte=year_end,
            type=leave_type if leave_type != 'leave' else 'leave'
        )
        
        # For "leave" type, also include half_day
        if leave_type == 'leave':
            dayoffs = DayOff.objects.filter(
                staff=self.user,
                status='approved',
                start_date__gte=year_start,
                start_date__lte=year_end,
                type__in=['leave', 'half_day']
            )
        
        # Calculate total used
        total_used = sum(abs(dayoff.leave_deduction) for dayoff in dayoffs)
        
        # Get the appropriate allowance
        if leave_type == 'sick':
            allowance = float(self.sick_leave_allowance)
        elif leave_type == 'other':
            total_added = sum(dayoff.leave_deduction for dayoff in dayoffs)
            return float(self.other_balance) + total_added
        else:  # leave (includes half_day)
            allowance = float(self.annual_leave_allowance)
        
        # Remaining = Allowance - Used
        remaining = allowance - total_used
        return round(remaining, 1)
    
    def get_leave_used(self, year=None, leave_type='leave'):
        """Calculate total leave used for the year by type"""
        if year is None:
            year = timezone.now().year
        
        year_start = datetime(year, 1, 1).date()
        year_end = datetime(year, 12, 31).date()
        
        # For "leave" type, include both leave and half_day
        if leave_type == 'leave':
            dayoffs = DayOff.objects.filter(
                staff=self.user,
                status='approved',
                start_date__gte=year_start,
                start_date__lte=year_end,
                type__in=['leave', 'half_day']
            )
        else:
            dayoffs = DayOff.objects.filter(
                staff=self.user,
                status='approved',
                start_date__gte=year_start,
                start_date__lte=year_end,
                type=leave_type
            )
        
        # For "other", return total added (positive)
        if leave_type == 'other':
            total_added = sum(dayoff.leave_deduction for dayoff in dayoffs)
            return round(total_added, 1)
        
        # For leave/sick, return total used (as positive number)
        total_used = sum(abs(dayoff.leave_deduction) for dayoff in dayoffs)
        return round(total_used, 1)


class DayOff(models.Model):
    """Track staff day-offs, vacations, and time off"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Updated leave types with specific deductions
    TYPE_CHOICES = [
        ('leave', 'Leave'),           # -1 day per day (or -0.5 for half day)
        ('sick', 'Sick Leave'),       # -1 day per day
        ('half_day', 'Half Day'),     # -0.5 days
        ('other', 'Other/Compensation'), # Always +1 (bonus/compensation)
    ]
    
    # Deduction rates for each leave type
    TYPE_DEDUCTIONS = {
        'leave': -1.0,      # Normal leave: -1 day per day
        'sick': -1.0,       # Sick leave: -1 day per day
        'half_day': -0.5,   # Half day: -0.5 days
        'other': 1.0,       # Other: ALWAYS +1 (not per day)
    }
    
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='day_offs'
    )
    
    # Date Range
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))
    
    # Details
    type = models.CharField(
        _("Type"),
        max_length=20,
        choices=TYPE_CHOICES,
        default='leave'
    )
    reason = models.TextField(_("Reason"), blank=True)
    
    # Approval
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_day_offs'
    )
    approval_date = models.DateTimeField(_("Approval Date"), null=True, blank=True)
    approval_notes = models.TextField(_("Approval Notes"), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Day Off")
        verbose_name_plural = _("Days Off")
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['staff', 'start_date']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.staff.name or self.staff.username} - {self.start_date} to {self.end_date}"
    
    @property
    def duration_days(self):
        """Calculate total calendar days in the range"""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def leave_deduction(self):
        """
        Calculate how much leave is deducted/added based on type
        
        - Leave: -1 day per day
        - Sick Leave: -1 day per day  
        - Half Day: -0.5 days (regardless of duration)
        - Other: ALWAYS +1 (compensation, not based on days)
        """
        if self.type == 'half_day':
            # Half day is always -0.5 regardless of duration
            return -0.5
        elif self.type == 'other':
            # Other is ALWAYS +1, not per day
            return 1.0
        else:
            # For leave and sick, multiply daily rate by duration
            daily_rate = self.TYPE_DEDUCTIONS.get(self.type, 0)
            return daily_rate * self.duration_days
    
    @property
    def is_upcoming(self):
        """Check if day off is in the future"""
        return self.start_date > timezone.now().date()
    
    @property
    def is_active(self):
        """Check if currently on day off"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    @property
    def is_past(self):
        """Check if day off has passed"""
        return self.end_date < timezone.now().date()
    
    def clean(self):
        """Validate the day off"""
        from django.core.exceptions import ValidationError
        
        if self.end_date < self.start_date:
            raise ValidationError(_("End date must be after start date"))
        
        # For half day, start and end date should be the same
        if self.type == 'half_day' and self.start_date != self.end_date:
            raise ValidationError(_("Half day leave must be for a single day"))
        
        # Check for overlapping day-offs for the same staff
        overlapping = DayOff.objects.filter(
            staff=self.staff,
            status='approved'
        ).exclude(pk=self.pk).filter(
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        
        if overlapping.exists():
            raise ValidationError(_("This overlaps with an existing approved day off"))
    
    def approve(self, approved_by_user):
        """Approve the day off"""
        self.status = 'approved'
        self.approved_by = approved_by_user
        self.approval_date = timezone.now()
        self.save()
    
    def reject(self, approved_by_user, notes=""):
        """Reject the day off"""
        self.status = 'rejected'
        self.approved_by = approved_by_user
        self.approval_date = timezone.now()
        self.approval_notes = notes
        self.save()