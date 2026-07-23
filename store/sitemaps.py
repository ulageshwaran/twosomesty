from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Category


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Adjust 'is_active' if your Product model uses a different field name
        # for tracking whether a product should be publicly visible
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        # Remove this method if your Product model has no 'updated_at' field
        return getattr(obj, 'updated_at', None)

    def location(self, obj):
        return reverse('store:product_detail', kwargs={'slug': obj.slug})


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('store:category_detail', kwargs={'slug': obj.slug})


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ['store:home']

    def location(self, item):
        return reverse(item)