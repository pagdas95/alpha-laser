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
    
    @property
    def is_complete(self):
        """
        A visit is complete when it has been fully paid (grand_total).
        Treatment parameters are optional — staff may not always fill them.
        """
        return self.paid_amount >= self.grand_total

    def get_missing_fields(self):
        """
        Return list of issues shown in the notification bell.
        Only flags unpaid/partially paid visits — treatment fields are optional.
        """
        missing = []

        if self.paid_amount < self.grand_total:
            outstanding = self.grand_total - self.paid_amount
            missing.append(f"Payment (€{outstanding:.2f} outstanding)")

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

    @property
    def products_total(self):
        """Sum of all products purchased during this visit"""
        # Fast path: value already computed by annotate_totals() — no extra query
        annotated = self.__dict__.get('products_total_db')
        if annotated is not None:
            return annotated
        from django.db.models import Sum, F as DbF
        result = self.visit_products.aggregate(
            total=Sum(DbF('price_at_time') * DbF('quantity'))
        )['total']
        return result or 0

    @property
    def grand_total(self):
        """Service charge + products total"""
        return self.charge_amount + self.products_total
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Visit"
        verbose_name_plural = "Visits"
    
    def __str__(self):
        return f"Visit for {self.appointment.client.full_name} - {self.appointment.start:%d/%m/%Y}"


def annotate_totals(queryset):
    """
    Annotate a Visit queryset with products_total_db and
    grand_total_db (= charge_amount + sum of VisitProduct line totals),
    computed in ONE query. Visit.products_total / grand_total / is_complete
    then use these values instead of querying once per visit.
    """
    from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Subquery, Sum
    from django.db.models.functions import Coalesce
    from alpha.products.models import VisitProduct

    money = DecimalField(max_digits=10, decimal_places=2)
    products_subq = (
        VisitProduct.objects
        .filter(visit=OuterRef('pk'))
        .values('visit')
        .annotate(pt=Sum(F('price_at_time') * F('quantity')))
        .values('pt')
    )
    return queryset.annotate(
        products_total_db=Coalesce(Subquery(products_subq, output_field=money), 0, output_field=money),
        grand_total_db=ExpressionWrapper(F('charge_amount') + F('products_total_db'), output_field=money),
    )


def recent_incomplete_visits(limit=10, recent=50):
    """
    The `limit` newest not-fully-paid visits among the `recent` newest visits
    (same rule the notification bell always used), in a single query.
    """
    from django.db.models import F

    recent_ids = Visit.objects.order_by('-created_at').values('pk')[:recent]
    return list(
        annotate_totals(
            Visit.objects.select_related(
                'appointment', 'appointment__client', 'appointment__service', 'staff'
            )
        )
        .filter(pk__in=recent_ids, paid_amount__lt=F('grand_total_db'))
        .order_by('-created_at')[:limit]
    )