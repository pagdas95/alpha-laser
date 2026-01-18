"""
Appointments Forms
Place this at: alpha/appointments/forms.py
"""
from django import forms
from .models import Appointment
from alpha.catalog.models import Service


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['client', 'service', 'staff', 'room', 'machine', 'start', 'end', 'status', 'notes', 'price_override']
        widgets = {
            'client': forms.Select(attrs={
                'data-trigger': '',
                'id': 'id_client',
            }),
            'service': forms.Select(attrs={
                'data-trigger': '',
                'id': 'id_service',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove status field for create form
        if not self.instance.pk:
            self.fields.pop('status', None)
        
        # Group services by category
        self._group_services_by_category()
    
    def _group_services_by_category(self):
        """Group services by their category"""
        services = Service.objects.select_related('category').order_by('category__name', 'name')
        
        grouped_choices = [('', 'Select a service...')]
        categories = {}
        
        for service in services:
            category_name = service.category.name if service.category else 'Other'
            if category_name not in categories:
                categories[category_name] = []
            categories[category_name].append((service.id, service.name))
        
        for category_name, service_list in sorted(categories.items()):
            grouped_choices.append((category_name, service_list))
        
        self.fields['service'].choices = grouped_choices


class AppointmentCreateForm(AppointmentForm):
    """Form for creating appointments (without status field)"""
    class Meta(AppointmentForm.Meta):
        fields = ['client', 'service', 'staff', 'room', 'machine', 'start', 'end', 'notes', 'price_override']


class AppointmentUpdateForm(AppointmentForm):
    """Form for updating appointments (with status field)"""
    pass

