from .models import Cart, CartItem

def get_or_create_cart(request):
    """
    Retrieves the current active cart.
    For logged-in users, returns the cart associated with their account.
    For guest users, returns the cart associated with their session key.
    """
    if not hasattr(request, "user"):
        return None

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Check if session exists, create if not
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def merge_carts(request, user):
    """
    Merges session/guest cart items into the authenticated user's cart upon login.
    If the same product variant exists in both carts, sums their quantities.
    Deletes the guest cart afterwards.
    """
    session_key = request.session.session_key
    if not session_key:
        return

    guest_carts = Cart.objects.filter(session_key=session_key, user=None)
    if not guest_carts.exists():
        return

    # Get or create the user's permanent cart
    user_cart, created = Cart.objects.get_or_create(user=user)

    for guest_cart in guest_carts:
        # Transfer items
        for guest_item in guest_cart.items.all():
            # Check if the variant already exists in the user's cart
            user_item, item_created = CartItem.objects.get_or_create(
                cart=user_cart,
                variant=guest_item.variant,
                defaults={'quantity': guest_item.quantity}
            )
            if not item_created:
                # If it already exists, add quantities
                user_item.quantity += guest_item.quantity
                user_item.save()
        
        # Merge coupon if user cart doesn't have one and guest cart has it
        if guest_cart.coupon and not user_cart.coupon:
            user_cart.coupon = guest_cart.coupon
            user_cart.save()
            
        guest_cart.delete()


import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def send_owner_whatsapp_alert(order):
    """
    Sends a WhatsApp notification to the store owner using CallMeBot free API.
    """
    try:
        phone = getattr(settings, 'OWNER_WHATSAPP_NUMBER', None)
        apikey = getattr(settings, 'CALLMEBOT_APIKEY', None)
        
        if not phone or not apikey or apikey == 'your-apikey':
            logger.warning("WhatsApp alert skipped: OWNER_WHATSAPP_NUMBER or CALLMEBOT_APIKEY is not configured.")
            return False
            
        customer_name = order.user.username if order.user else 'Guest'
        items_count = order.items.count()
        
        # Build a short message
        message = (
            f"New Order Confirmed!\n"
            f"Order ID: #{order.id}\n"
            f"Customer: {customer_name}\n"
            f"Total: Rs. {order.total_amount}\n"
            f"Items: {items_count}"
        )
        
        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            'phone': phone,
            'text': message,
            'apikey': apikey
        }
        
        # Short timeout (5s), wrapped in try/except so it never breaks order processing
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            logger.info(f"WhatsApp alert sent successfully for Order #{order.id}.")
            return True
        else:
            logger.error(f"Failed to send WhatsApp alert for Order #{order.id}. Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logger.exception(f"Exception occurred while sending WhatsApp alert for Order #{order.id}: {e}")
        return False


def send_order_notifications(order, request=None):
    """
    Triggers automated customer email, owner email, and owner WhatsApp alerts.
    Marks notification_sent=True upon completion.
    """
    if order.notification_sent:
        return
        
    logger.info(f"Triggering order notifications helper for Order #{order.id}...")
    
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    # 1. Determine absolute base URL for image links in HTML emails
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        # Fallback if no request is active (e.g. from signals/webhook context)
        base_url = "http://127.0.0.1:8000"
        
    context = {
        'order': order,
        'base_url': base_url
    }

    # 2. Send customer confirmation email
    try:
        recipient_email = order.user.email if order.user else None
        if recipient_email:
            subject = f"Order Confirmation - Twosomesty (Order #{order.id})"
            # Render HTML version and plain-text fallback
            html_message = render_to_string('emails/order_confirmation_customer.html', context)
            plain_message = render_to_string('emails/order_confirmation_customer.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Confirmation email sent to customer ({recipient_email}) for Order #{order.id}.")
        else:
            logger.warning(f"No customer email found to send confirmation for Order #{order.id}.")
    except Exception as e:
        logger.exception(f"Failed to send customer confirmation email for Order #{order.id}: {e}")

    # 3. Send owner notification email
    try:
        owner_email = getattr(settings, 'OWNER_EMAIL', None)
        if owner_email:
            subject = f"New Paid Order Received - Twosomesty (Order #{order.id})"
            # Render HTML version and plain-text fallback
            html_message = render_to_string('emails/order_confirmation_owner.html', context)
            plain_message = render_to_string('emails/order_confirmation_owner.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"New order notification email sent to store owner ({owner_email}) for Order #{order.id}.")
        else:
            logger.warning(f"OWNER_EMAIL setting is not configured. Skipping owner email for Order #{order.id}.")
    except Exception as e:
        logger.exception(f"Failed to send owner confirmation email for Order #{order.id}: {e}")

    # 4. Send WhatsApp notification to Store Owner
    try:
        send_owner_whatsapp_alert(order)
    except Exception as e:
        logger.exception(f"Failed to trigger WhatsApp alert for Order #{order.id}: {e}")

    # 5. Save notification_sent status flag to database
    try:
        order.notification_sent = True
        order.save(update_fields=['notification_sent'])
        logger.info(f"Set notification_sent=True for Order #{order.id}.")
    except Exception as e:
        logger.exception(f"Failed to update notification_sent flag for Order #{order.id}: {e}")
