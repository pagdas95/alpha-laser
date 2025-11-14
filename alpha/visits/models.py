from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

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