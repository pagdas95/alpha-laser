from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

class Visit(models.Model):
    appointment = models.OneToOneField("appointments.Appointment", on_delete=models.CASCADE, related_name="visit")
    staff       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits")
    machine     = models.ForeignKey("resources.Machine", on_delete=models.SET_NULL, null=True, blank=True)

    area            = models.CharField("Περιοχή", max_length=64, blank=True)
    spot_size_mm    = models.DecimalField("Spot size (mm)", max_digits=4, decimal_places=1, null=True, blank=True)
    fluence_j_cm2   = models.DecimalField("Ενέργεια (J/cm²)", max_digits=6, decimal_places=2, null=True, blank=True)
    pulse_count     = models.PositiveIntegerField("Παλμοί", null=True, blank=True)
    remarks         = models.TextField("Παρατηρήσεις", blank=True)

    charge_amount   = models.DecimalField("Χρέωση", max_digits=8, decimal_places=2)
    paid_amount     = models.DecimalField("Πληρωμή", max_digits=8, decimal_places=2, default=0)
    payment_method  = models.CharField("Μέθοδος", max_length=16, choices=[("cash","Μετρητά"),("card","Κάρτα"),("other","Άλλο")], blank=True)

    client_package_item = models.ForeignKey(
        "catalog.ClientPackageItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="visits",
        verbose_name="Συνεδρία από Πακέτο"
    )
    
    # ✅ NEW: Tracking timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.client_package_item:
            pkg_service_id = self.client_package_item.package_item.service_id
            appt_service_id = self.appointment.service_id
            if pkg_service_id != appt_service_id:
                raise ValidationError("Το πακέτο δεν αντιστοιχεί στην υπηρεσία του ραντεβού.")

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Default staff/machine from appointment if missing
        if not self.staff_id:
            self.staff = self.appointment.staff
        if not self.machine_id and self.appointment.machine_id:
            self.machine = self.appointment.machine
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and self.client_package_item:
            # decrement exactly once on first save
            self.client_package_item.redeem_one()
    
    # ✅ NEW: Check if visit record is complete
    @property
    def is_complete(self):
        """
        A visit is considered complete if:
        - Has treatment area
        - Has at least one treatment parameter (spot_size, fluence, or pulse_count)
        - Payment information is recorded (paid_amount > 0 OR payment_method is set)
        """
        has_area = bool(self.area and self.area.strip())
        has_treatment_params = any([
            self.spot_size_mm is not None,
            self.fluence_j_cm2 is not None,
            self.pulse_count is not None
        ])
        has_payment_info = self.paid_amount > 0 or bool(self.payment_method)
        
        return has_area and has_treatment_params and has_payment_info
    
    # ✅ NEW: Get missing fields for notification display
    def get_missing_fields(self):
        """Return list of missing required fields"""
        missing = []
        
        if not (self.area and self.area.strip()):
            missing.append("Treatment Area")
        
        if not any([self.spot_size_mm, self.fluence_j_cm2, self.pulse_count]):
            missing.append("Treatment Parameters")
        
        if self.paid_amount == 0 and not self.payment_method:
            missing.append("Payment Information")
        
        return missing
    
    # ✅ NEW: Time since creation for notifications
    def time_since_creation(self):
        """Return human-readable time since visit was created"""
        if not hasattr(self, 'created_at'):
            return "Unknown"
        
        delta = timezone.now() - self.created_at
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Visit"
        verbose_name_plural = "Visits"
    
    def __str__(self):
        return f"Visit for {self.appointment.client.full_name} - {self.appointment.start:%d/%m/%Y}"