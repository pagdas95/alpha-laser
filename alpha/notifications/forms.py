from django import forms
from django.utils.translation import gettext_lazy as _
from .models import NotificationTemplate  # ✨ ADDED


class BulkNotificationForm(forms.Form):
    """Form for sending bulk notifications"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('sms', _('SMS Only')),
        ('email', _('Email Only')),
        ('both', _('Both SMS and Email')),
    ]
    
    # ✨ NEW: Template selector
    template = forms.ModelChoiceField(
        label=_("Use Template"),
        queryset=NotificationTemplate.objects.filter(is_active=True),
        required=False,
        empty_label=_("-- Choose a template (optional) --"),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'templateSelect'
        })
    )
    
    notification_type = forms.ChoiceField(
        label=_("Notification Type"),
        choices=NOTIFICATION_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='both'
    )
    
    # Email fields
    email_subject = forms.CharField(
        label=_("Email Subject"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter email subject...')
        })
    )
    
    email_message = forms.CharField(
        label=_("Email Message"),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': _('Enter email message...')
        })
    )
    
    # SMS fields
    sms_message = forms.CharField(
        label=_("SMS Message"),
        required=False,
        max_length=160,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Enter SMS message (max 160 characters)...'),
            'maxlength': 160
        }),
        help_text=_("Keep SMS messages short and concise (max 160 characters)")
    )
    
    # Client selection
    send_to_all = forms.BooleanField(
        label=_("Send to All Clients"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    selected_clients = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        notification_type = cleaned_data.get('notification_type')
        email_subject = cleaned_data.get('email_subject')
        email_message = cleaned_data.get('email_message')
        sms_message = cleaned_data.get('sms_message')
        send_to_all = cleaned_data.get('send_to_all')
        selected_clients = cleaned_data.get('selected_clients')
        
        # Validate email fields
        if notification_type in ['email', 'both']:
            if not email_subject:
                raise forms.ValidationError(_("Email subject is required when sending emails"))
            if not email_message:
                raise forms.ValidationError(_("Email message is required when sending emails"))
        
        # Validate SMS fields
        if notification_type in ['sms', 'both']:
            if not sms_message:
                raise forms.ValidationError(_("SMS message is required when sending SMS"))
        
        # Validate recipient selection
        if not send_to_all and not selected_clients:
            raise forms.ValidationError(_("Please select at least one client or choose 'Send to All'"))
        
        return cleaned_data


class ClientSelectionForm(forms.Form):
    """Form for selecting clients for bulk notifications"""
    
    search_query = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by name, phone, or email...')
        })
    )
    
    has_email = forms.BooleanField(
        label=_("Has Email"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    has_phone = forms.BooleanField(
        label=_("Has Phone"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


# ✨ NEW: Template form for creating/editing templates
class NotificationTemplateForm(forms.ModelForm):
    """Form for creating/editing notification templates"""
    
    class Meta:
        model = NotificationTemplate
        fields = ['name', 'notification_type', 'sms_body', 'email_subject', 'email_body', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Birthday Special')
            }),
            'notification_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'sms_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': 160,
                'placeholder': _('e.g., Happy Birthday {client_name}! Get 20% off this month!')
            }),
            'email_subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Happy Birthday!')
            }),
            'email_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': _('e.g., Dear {client_name}, celebrate your birthday with us!')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['is_active'].initial = True