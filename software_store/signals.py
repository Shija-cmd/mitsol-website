from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SoftwareLicense, SoftwareOrder


@receiver(post_save, sender=SoftwareOrder)
def create_license_for_paid_order(sender, instance, **kwargs):

    if instance.payment_status != SoftwareOrder.PaymentStatus.PAID:

        return

    SoftwareLicense.objects.get_or_create(
        order=instance,
        defaults={
            'product': instance.product,
            'customer_name': instance.customer_name,
            'customer_email': instance.customer_email,
            'allowed_devices': 1,
            'is_active': True,
        }
    )
