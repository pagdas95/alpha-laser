from django.conf import settings
from django.db import models

class Appointment(models.Model):
    STATUS_CHOICES = [
        ("booked","Κλεισμένο"), ("completed","Ολοκληρώθηκε"),
        ("no_show","Δεν προσήλθε"), ("cancelled","Ακυρώθηκε"),
    ]
    client  = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="appointments")
    service = models.ForeignKey("catalog.Service", on_delete=models.PROTECT)
    staff   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appointments")
    room    = models.ForeignKey("resources.Room", on_delete=models.PROTECT)
    machine = models.ForeignKey("resources.Machine", on_delete=models.PROTECT, null=True, blank=True)
    start   = models.DateTimeField()
    end     = models.DateTimeField()
    status  = models.CharField(max_length=16, choices=STATUS_CHOICES, default="booked")
    notes   = models.TextField(blank=True)
    price_override = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["start"]),
            models.Index(fields=["room","start"]),
            models.Index(fields=["staff","start"]),
        ]
        ordering = ["-start"]

    def __str__(self):
        return f"{self.client} – {self.service} @ {self.start:%d/%m %H:%M}"