from django.contrib import admin
from .models import (
    Profile, Address, Category, Product, ProductImage, 
    ProductVariant, Cart, CartItem, Coupon, Order, OrderItem, Wishlist, ProductReview, CarouselSlide, StoreFeature
)

# Inlines
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    prepopulated_fields = {'sku': ('size', 'color')} # optional helpers


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_image_thumbnail', 'variant', 'quantity', 'price_at_purchase', 'total_price')
    fields = ('product_image_thumbnail', 'variant', 'quantity', 'price_at_purchase', 'total_price')
    can_delete = False

    def product_image_thumbnail(self, obj):
        if obj.variant and obj.variant.product:
            first_image = obj.variant.product.images.first()
            if first_image and first_image.image:
                from django.utils.html import format_html
                return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;" />', first_image.image.url)
        return "-"
    product_image_thumbnail.short_description = 'Image'


# Admin Registries
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'line1', 'city', 'state', 'pincode', 'is_default')
    list_filter = ('state', 'is_default')
    search_fields = ('user__username', 'line1', 'city', 'pincode')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'meta_title')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
    list_filter = ('parent',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_price', 'discount_price', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'brand', 'slug', 'variants__sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'sku', 'size', 'color', 'stock_qty', 'price_override', 'price')
    list_filter = ('size', 'color')
    search_fields = ('sku', 'product__name')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'created_at', 'updated_at')
    search_fields = ('user__username', 'session_key')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'variant', 'quantity', 'total_price')
    search_fields = ('cart__user__username', 'variant__sku')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'razorpay_order_id', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('id', 'user__username', 'razorpay_order_id')
    inlines = [OrderItemInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_image_thumbnail', 'order', 'variant', 'quantity', 'price_at_purchase', 'total_price')
    readonly_fields = ('product_image_thumbnail',)
    fields = ('product_image_thumbnail', 'order', 'variant', 'quantity', 'price_at_purchase')
    search_fields = ('order__id', 'variant__sku')

    def product_image_thumbnail(self, obj):
        if obj.variant and obj.variant.product:
            first_image = obj.variant.product.images.first()
            if first_image and first_image.image:
                from django.utils.html import format_html
                return format_html('<img src="{}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 8px;" />', first_image.image.url)
        return "-"
    product_image_thumbnail.short_description = 'Image'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')


@admin.register(CarouselSlide)
class CarouselSlideAdmin(admin.ModelAdmin):
    list_display = ('slide_image_thumbnail', 'title', 'subtitle', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'subtitle', 'description')
    ordering = ('order', 'id')
    list_editable = ('order', 'is_active')

    def slide_image_thumbnail(self, obj):
        if obj.image:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="width: 100px; height: 50px; object-fit: cover; border-radius: 6px;" />', obj.image.url)
        return "-"
    slide_image_thumbnail.short_description = 'Image Preview'


@admin.register(StoreFeature)
class StoreFeatureAdmin(admin.ModelAdmin):
    list_display = ('feature_image_thumbnail', 'title', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    ordering = ('order', 'id')
    list_editable = ('order', 'is_active')

    def feature_image_thumbnail(self, obj):
        if obj.image:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;" />', obj.image.url)
        return "-"
    feature_image_thumbnail.short_description = 'Icon/Image'
