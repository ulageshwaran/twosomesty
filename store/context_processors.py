from django.core.cache import cache
from .models import Category
from .utils import get_or_create_cart

def categories_processor(request):
    """
    Passes top-level categories to all templates for the header navigation.
    Caches results to avoid database network roundtrips on every page hit.
    """
    nav_categories = cache.get('nav_categories')
    if nav_categories is None:
        nav_categories = list(Category.objects.filter(parent=None).prefetch_related('subcategories'))
        cache.set('nav_categories', nav_categories, 300)
    return {
        'nav_categories': nav_categories
    }


def cart_processor(request):
    """
    Passes the shopping cart object and total item count to all templates with prefetched items.
    """
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related('variant', 'variant__product').all())
    cart_count = sum(item.quantity for item in items)
    return {
        'cart': cart,
        'cart_count': cart_count
    }

def wishlist_processor(request):
    """
    Passes list of wishlisted product IDs to all templates.
    """
    if request.user.is_authenticated:
        wishlist_product_ids = set(request.user.wishlists.values_list('product_id', flat=True))
    else:
        wishlist_product_ids = set()
    return {
        'wishlist_product_ids': wishlist_product_ids
    }

def logo_processor(request):
    """
    Passes Cloudinary URLs for logo images to all templates with local static fallback.
    """
    # pyrefly: ignore [missing-import]
    import cloudinary.utils
    try:
        # Generate optimized, secure Cloudinary URLs
        brand_logo_url = cloudinary.utils.cloudinary_url("brand_logo", secure=True)[0]
        logo_footer_url = cloudinary.utils.cloudinary_url("logo_footer", secure=True)[0]
    except Exception:
        # Fallback to local static paths if error occurs
        from django.templatetags.static import static
        brand_logo_url = static("images/brand_logo.PNG")
        logo_footer_url = static("images/logo_footer.png")
        
    return {
        'brand_logo_url': brand_logo_url,
        'logo_footer_url': logo_footer_url,
    }
