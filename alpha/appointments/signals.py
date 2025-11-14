from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment

@receiver(post_save, sender=Appointment)
def create_visit_on_completion(sender, instance, created, **kwargs):
    """
    Automatically create a Visit when appointment status changes to 'completed'
    """
    # Only for existing appointments that just became 'completed'
    if not created and instance.status == 'completed':
        # Check if visit doesn't already exist
        if not hasattr(instance, 'visit'):
            from alpha.visits.models import Visit  # Import here to avoid circular import
            
            Visit.objects.create(
                appointment=instance,
                staff=instance.staff,
                machine=instance.machine,
                charge_amount=instance.price_override or 0,
                paid_amount=0  # Will be filled in by staff later
            )