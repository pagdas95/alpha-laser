# alpha/staff/forms.py
from django import forms
from .models import DayOff, StaffProfile
from alpha.users.models import User


class DayOffForm(forms.ModelForm):
    """Form for creating/editing day-off requests"""
    
    class Meta:
        model = DayOff
        fields = ['staff', 'start_date', 'end_date', 'type', 'reason']  # Removed 'status'
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional reason'}),
        }
        help_texts = {
            'type': 'Leave/Sick: -1 day per day | Half Day: -0.5 days | Other: ALWAYS +1 (compensation)',
        }
    
    def __init__(self, *args, **kwargs):
        # If staff_user is passed, hide the staff field and pre-select it
        staff_user = kwargs.pop('staff_user', None)
        super().__init__(*args, **kwargs)
        
        if staff_user:
            self.fields['staff'].initial = staff_user
            self.fields['staff'].widget = forms.HiddenInput()
        
        # Only show staff members
        self.fields['staff'].queryset = User.objects.filter(is_staff=True)
        
        # Add CSS classes and help text
        self.fields['type'].widget.attrs.update({
            'onchange': 'updateDateFields(this.value)'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('type')
        
        if not start_date:
            raise forms.ValidationError("Please select a start date")
        
        if not end_date:
            raise forms.ValidationError("Please select an end date")
        
        if not leave_type:
            raise forms.ValidationError("Please select a leave type")
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be before start date")
            
            # For half day, enforce same day
            if leave_type == 'half_day' and start_date != end_date:
                raise forms.ValidationError("Half day leave must be for a single day. Please set start and end date to the same day.")
        
        return cleaned_data


class StaffProfileForm(forms.ModelForm):
    """Form for editing staff profile"""
    
    class Meta:
        model = StaffProfile
        fields = [
            'position', 'employment_type', 'hire_date', 'employee_id',
            'phone', 'emergency_contact', 'emergency_phone',
            'certifications', 'specializations', 'bio',
            'avatar', 
            'annual_leave_allowance', 'sick_leave_allowance', 'other_balance',
            'is_active_staff', 'can_be_booked'
        ]
        widgets = {
            # Position is now a TEXT INPUT (not dropdown)
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Laser Technician, Senior Nurse, Receptionist'
            }),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+357 99 123456'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name and relationship'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+357 99 123456'}),
            'certifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'specializations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'annual_leave_allowance': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'sick_leave_allowance': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'other_balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'is_active_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_be_booked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'position': 'Enter the staff member\'s position (free text)',
            'annual_leave_allowance': 'Regular leave days per year (includes half days)',
            'sick_leave_allowance': 'Sick leave days allowed per year',
            'other_balance': 'Current balance of compensation/bonus days',
        }