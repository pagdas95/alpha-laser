from django.db import models

# Create your models here.
class Room(models.Model):
    name = models.CharField("Όνομα Δωματίου", max_length=32, unique=True)
    is_active = models.BooleanField("Ενεργό", default=True)

    def __str__(self):
        return self.name

class Machine(models.Model):
    name = models.CharField("Μηχάνημα", max_length=64)
    notes = models.TextField("Σημειώσεις", blank=True)
    is_active = models.BooleanField("Ενεργό", default=True)

    def __str__(self):
        return self.name