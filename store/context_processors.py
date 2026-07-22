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
