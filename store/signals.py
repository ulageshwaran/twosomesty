from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


import logging
from django.dispatch import receiver
from .models import Order
from .utils import send_order_notifications

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order)
def send_order_confirmation_notifications(sender, instance, **kwargs):
    """
    Sends automated email and WhatsApp alerts when order payment is confirmed.
    Fires only when payment_status is 'Paid' and notification_sent is False, 
    and only if the order already has associated items (i.e. updated post-creation).
    """
    if instance.payment_status == 'Paid' and not instance.notification_sent:
        if instance.items.exists():
            logger.info(f"Order #{instance.id} paid status updated. Running notifications from signal...")
            send_order_notifications(instance)
        else:
            logger.info(f"Order #{instance.id} created as Paid but has no items yet. Post-save signal deferred.")


