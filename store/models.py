from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# 1. Profile Model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# 2. Address Model
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=255, default='')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, default='')
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other default addresses for this user to False
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name or self.user.username} - {self.line1}, {self.city}"

    class Meta:
        verbose_name_plural = "Addresses"


# 3. Category Model
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=120, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    
    # Local SEO targeting Chennai / Tamil Nadu
    meta_title = models.CharField(max_length=150, blank=True, null=True)
    meta_description = models.TextField(max_length=250, blank=True, null=True)
    og_image = models.ImageField(upload_to='categories/og/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "category"
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Prevent parent dependency cycles
        if self.parent:
            if self.pk and self.parent.pk == self.pk:
                raise ValueError("A category cannot be its own parent.")
            k = self.parent
            visited = {self.pk} if self.pk else set()
            while k is not None:
                if k.pk in visited:
                    raise ValueError("Circular dependency detected in Category hierarchy.")
                if k.pk:
                    visited.add(k.pk)
                k = k.parent
        
        # Populate defaults for local SEO if empty
        if not self.meta_title:
            self.meta_title = f"Buy {self.name} Online in Chennai | Twosomesty"
        if not self.meta_description:
            self.meta_description = f"Shop premium {self.name.lower()} online at Twosomesty. Fast delivery in Chennai and across Tamil Nadu."
            
        from django.core.cache import cache
        cache.delete('nav_categories')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.cache import cache
        cache.delete('nav_categories')
        super().delete(*args, **kwargs)

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        visited = {self.pk} if self.pk else set()
        while k is not None:
            if k.pk in visited:
                full_path.append(f"[LOOP: {k.name}]")
                break
            if k.pk:
                visited.add(k.pk)
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

    class Meta:
        verbose_name_plural = "Categories"


# 4. Product Model
class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    brand = models.CharField(max_length=100, default='Twosomesty')
    fabric = models.CharField(max_length=150, default='100% Organic Combed Cotton (Heavyweight)')
    weight = models.CharField(max_length=100, default='240 GSM (Oversized) / 400 GSM (Hoodies)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Local SEO targeting Chennai / Tamil Nadu
    meta_title = models.CharField(max_length=150, blank=True, null=True)
    meta_description = models.TextField(max_length=250, blank=True, null=True)
    og_image = models.ImageField(upload_to='products/og/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "product"
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        # Populate defaults for local SEO if empty
        if not self.meta_title:
            self.meta_title = f"{self.name} - Buy Online in Chennai, Tamil Nadu | Twosomesty"
        if not self.meta_description:
            # Truncate description text for meta description
            desc_snippet = self.description[:150] if self.description else "Premium clothing"
            self.meta_description = f"{desc_snippet}. Available online at Twosomesty with fast shipping across Tamil Nadu."
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        return sum(self.variants.values_list('stock_qty', flat=True))

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews.exists():
            return 0.0
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    @property
    def reviews_count(self):
        return self.reviews.count()

    @property
    def primary_image_url(self):
        first_img = self.images.first()
        if first_img:
            return first_img.get_optimized_url(width=1400, quality="90")
        return ''

    @property
    def primary_thumbnail_url(self):
        first_img = self.images.first()
        if first_img:
            return first_img.get_optimized_url(width=800, quality="90")
        return ''


# 5. ProductImage Model
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.name}"

    def get_optimized_url(self, width=1400, height=None, crop="limit", quality="90", fetch_format="auto"):
        if not self.image:
            return ''
        url = self.image.url
        if 'res.cloudinary.com' in url and '/upload/' in url:
            params = [f"f_{fetch_format}", f"q_{quality}"]
            if width:
                params.append(f"w_{width}")
            if height:
                params.append(f"h_{height}")
            if crop:
                params.append(f"c_{crop}")
            param_str = ','.join(params)
            return url.replace('/upload/', f'/upload/{param_str}/')
        return url

    @property
    def optimized_url(self):
        return self.get_optimized_url(width=1600, quality="90")

    @property
    def thumbnail_url(self):
        return self.get_optimized_url(width=800, quality="90")


# 6. ProductVariant Model
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=20)
    color = models.CharField(max_length=50)
    stock_qty = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    @property
    def price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.discount_price if self.product.discount_price else self.product.base_price

    def __str__(self):
        return f"{self.product.name} ({self.size} / {self.color})"


# 7. Cart Model
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        from decimal import Decimal
        return sum((item.total_price for item in self.items.all()), Decimal('0.00'))

    @property
    def discount_amount(self):
        from decimal import Decimal
        if not self.coupon or not self.coupon.is_active:
            return Decimal('0.00')
        
        from django.utils import timezone
        now = timezone.now()
        if self.coupon.valid_from <= now <= self.coupon.valid_to:
            if self.coupon.discount_type == 'P':
                return (self.subtotal * self.coupon.discount_value / Decimal('100.00')).quantize(Decimal('0.01'))
            elif self.coupon.discount_type == 'F':
                return min(self.coupon.discount_value, self.subtotal)
        return Decimal('0.00')

    @property
    def shipping_amount(self):
        from decimal import Decimal
        sub = self.subtotal
        if sub == Decimal('0.00'):
            return Decimal('0.00')
        # Count jackets
        jacket_qty = sum(item.quantity for item in self.items.all() if item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
        if jacket_qty >= 3:
            return Decimal('200.00')
        return Decimal('100.00')

    @property
    def tax_amount(self):
        from decimal import Decimal
        return Decimal('0.00')

    @property
    def total_price(self):
        from decimal import Decimal
        return max(Decimal('0.00'), self.subtotal - self.discount_amount + self.shipping_amount)

    @property
    def total_excluding_shipping(self):
        from decimal import Decimal
        return max(Decimal('0.00'), self.subtotal - self.discount_amount)

    def __str__(self):
        if self.user:
            return f"Cart of User: {self.user.username}"
        return f"Guest Cart: {self.session_key}"


# 8. CartItem Model
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.variant.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.variant}"


# 9. Coupon Model
class Coupon(models.Model):
    DISCOUNT_CHOICES = [
        ('F', 'Flat Amount'),
        ('P', 'Percentage'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=1, choices=DISCOUNT_CHOICES, default='F')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        type_str = "Flat" if self.discount_type == 'F' else "%"
        return f"{self.code} ({self.discount_value} {type_str})"


# 10. Order Model
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_applied = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    payment_status = models.CharField(max_length=50, default='Pending')
    notification_sent = models.BooleanField(default=False)

    
    # Razorpay Payments
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    # Shipment Tracking
    shipping_partner = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def tracking_url(self):
        if not self.tracking_number:
            return None
        
        tn = self.tracking_number.strip()
        if tn.startswith("http://") or tn.startswith("https://"):
            return tn
            
        sp = (self.shipping_partner or "").strip().lower()
        
        if "bluedart" in sp or "blue dart" in sp:
            return "https://www.bluedart.com/tracking"
        elif "delhivery" in sp:
            return "https://www.delhivery.com/"
        elif "india post" in sp or "speed post" in sp or "indiapost" in sp:
            return "https://www.indiapost.gov.in/"
        elif "st courier" in sp or "stcourier" in sp or sp == "st" or sp.startswith("st "):
            return "https://stcourier.com/"
        elif "franch" in sp:
            return f"https://franchexpress.com/courier-tracking?AWB={tn}"
        elif "dtdc" in sp:
            return "https://www.dtdc.com/in/"
        elif "ekart" in sp:
            return f"https://ekartlogistics.com/shipmenttrack/{tn}"
        elif "shadowfax" in sp:
            return "https://www.shadowfax.in/"
        elif "xpressbees" in sp or "expressbees" in sp:
            return "https://www.xpressbees.com/"
        elif "professional" in sp or "tpc" in sp:
            return "https://www.tpcindia.com/"
        elif "fedex" in sp:
            return "https://www.fedex.com/en-in/tracking.html"
        elif "dhl" in sp:
            return f"https://www.dhl.com/en/express/tracking.html?AWB={tn}"
        else:
            return f"https://www.google.com/search?q={self.shipping_partner or 'courier'}+{tn}+tracking".replace(' ', '+')

    @property
    def payment_method(self):
        if self.razorpay_payment_id or self.razorpay_order_id:
            return "Razorpay (UPI / Cards / Netbanking)"
        return "Online Payment"

    @property
    def subtotal(self):
        from decimal import Decimal
        return sum(Decimal(str(item.price_at_purchase)) * item.quantity for item in self.items.all() if item.price_at_purchase is not None)

    @property
    def discount_amount(self):
        from decimal import Decimal
        if not self.coupon_applied:
            return Decimal('0.00')
        sub = self.subtotal
        if self.coupon_applied.discount_type == 'F': # Flat
            return min(Decimal(str(self.coupon_applied.discount_value)), sub)
        else: # Percentage
            return sub * (Decimal(str(self.coupon_applied.discount_value)) / Decimal('100.00'))

    @property
    def shipping_amount(self):
        from decimal import Decimal
        sub = self.subtotal
        disc = self.discount_amount
        net = sub - disc
        # Count jackets in order items
        jacket_qty = sum(item.quantity for item in self.items.all() if item.variant and item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
        
        state_lower = ''
        if self.address and self.address.state:
            state_lower = self.address.state.strip().lower()
            
        is_tn = state_lower in ['tamil nadu', 'tamilnadu', 'tn']
        
        if jacket_qty >= 3:
            return Decimal('100.00') if is_tn else Decimal('200.00')
        else:
            return Decimal('50.00') if is_tn else Decimal('100.00')

    @property
    def tax_amount(self):
        from decimal import Decimal
        return Decimal('0.00')

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


# 11. OrderItem Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_price(self):
        if self.price_at_purchase is None:
            from decimal import Decimal
            return Decimal('0.00')
        return self.price_at_purchase * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.variant} in Order #{self.order.id}"


# 12. Wishlist Model
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


# 13. ProductReview Model
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating} Stars)"


# 14. CarouselSlide Model
class CarouselSlide(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='carousel/')
    button_text = models.CharField(max_length=50, default='Shop Now')
    button_link = models.CharField(max_length=255, default='#new-arrivals')
    order = models.PositiveIntegerField(default=0, help_text="Order in which slides appear")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Slide {self.order}: {self.title}"


# 15. StoreFeature Model
class StoreFeature(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    image = models.ImageField(upload_to='features/', blank=True, null=True, help_text="Upload an icon or image for this feature section")
    order = models.PositiveIntegerField(default=0, help_text="Ordering position")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title
