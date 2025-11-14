from django.db import models

# Create your models here.
class ServiceCategory(models.Model):
    name = models.CharField("Κατηγορία", max_length=80)
    def __str__(self): return self.name

class Service(models.Model):
    GENDER_CHOICES = [("any","Οποιοδήποτε"),("female","Γυναίκα"),("male","Άνδρας")]
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    name = models.CharField("Υπηρεσία", max_length=120)
    gender = models.CharField("Φύλο", max_length=10, choices=GENDER_CHOICES, default="any")
    default_price = models.DecimalField("Τιμή", max_digits=8, decimal_places=2)
    duration_min = models.PositiveIntegerField("Διάρκεια (λεπτά)", default=30)
    notes = models.TextField("Σημειώσεις", blank=True)

    class Meta:
        unique_together = [("category","name","gender")]

    def __str__(self):
        return self.name

class Package(models.Model):
    name = models.CharField("Πακέτο", max_length=120)
    price = models.DecimalField("Τιμή Πακέτου", max_digits=8, decimal_places=2)
    notes = models.TextField("Σημειώσεις", blank=True)
    def __str__(self): return self.name

class PackageItem(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    sessions = models.PositiveIntegerField("Συνεδρίες", default=1)
    def __str__(self): return f"{self.package} → {self.service} x{self.sessions}"

class ClientPackage(models.Model):
    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="packages")
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    purchased_at = models.DateTimeField(auto_now_add=True)
    price_paid = models.DecimalField(max_digits=8, decimal_places=2)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    def __str__(self): return f"{self.client} – {self.package}"

class ClientPackageItem(models.Model):
    client_package = models.ForeignKey(ClientPackage, on_delete=models.CASCADE, related_name="items")
    package_item = models.ForeignKey(PackageItem, on_delete=models.PROTECT)
    remaining_sessions = models.PositiveIntegerField(default=0)

    def redeem_one(self):
        if self.remaining_sessions == 0:
            raise ValueError("No remaining sessions.")
        self.remaining_sessions -= 1
        self.save(update_fields=["remaining_sessions"])

    def __str__(self):
        return f"{self.client_package} – {self.package_item.service} ({self.remaining_sessions} left)"