from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.db.models import Sum, Count, Q, Avg
from decimal import Decimal

from .models import (
    Product, ProductImage, ProductVariant, Category, Order, OrderItem, 
    Coupon, StoreFeature, CarouselSlide, Profile, ProductReview
)
from .mixins import StaffRequiredMixin
from .forms import ProductForm

# 1. Admin Authentication Views
class AdminLoginView(LoginView):
    template_name = 'store/admin/admin_login.html'
    redirect_authenticated_user = False

    def form_valid(self, form):
        user = form.get_user()
        if not (user.is_staff or user.is_superuser):
            messages.error(self.request, "Access denied. Regular customer accounts cannot log in to the Admin Portal.")
            return redirect('store:admin_login')
        auth_login(self.request, user)
        return redirect('store:admin_dashboard')


def admin_logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out of the Admin Portal.")
    return redirect('store:admin_login')


# 2. Executive Analytics Dashboard View
class AdminDashboardView(StaffRequiredMixin, View):
    def get(self, request):
        paid_orders = Order.objects.filter(payment_status='Paid')
        total_revenue = paid_orders.aggregate(revenue=Sum('total_amount'))['revenue'] or Decimal('0.00')
        paid_orders_count = paid_orders.count()
        total_orders_count = Order.objects.count()
        pending_orders_count = Order.objects.filter(Q(status='Pending') | Q(status='Processing')).count()
        active_products_count = Product.objects.filter(is_active=True).count()

        # Low stock variants (stock <= 5)
        low_stock_variants = ProductVariant.objects.filter(stock_qty__lte=5).select_related('product')
        low_stock_count = low_stock_variants.count()

        # Recent 10 orders
        recent_orders = Order.objects.all().order_by('-created_at')[:10]

        context = {
            'total_revenue': total_revenue,
            'paid_orders_count': paid_orders_count,
            'total_orders_count': total_orders_count,
            'pending_orders_count': pending_orders_count,
            'active_products_count': active_products_count,
            'low_stock_count': low_stock_count,
            'low_stock_variants': low_stock_variants[:6],
            'recent_orders': recent_orders,
        }
        return render(request, 'store/admin/dashboard.html', context)


# 3. Product & Inventory Management Views
class AdminProductListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = 'store/admin/product_list.html'
    context_object_name = 'products'
    ordering = ['-created_at']


class AdminProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    template_name = 'store/admin/product_form.html'
    fields = ['name', 'category', 'base_price', 'discount_price', 'description', 'brand', 'fabric', 'weight', 'is_active']

    def get_success_url(self):
        return reverse('store:admin_product_edit', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        product = self.object

        # Process uploaded images
        images = self.request.FILES.getlist('images')
        for idx, img in enumerate(images):
            ProductImage.objects.create(product=product, image=img, order=idx)

        # Handle initial manual variant if provided during creation
        new_size = self.request.POST.get('new_size', '').strip()
        new_color = self.request.POST.get('new_color', '').strip()
        new_stock = self.request.POST.get('new_stock', '').strip()
        new_sku = self.request.POST.get('new_sku', '').strip()

        if new_size and new_color and new_stock:
            if not new_sku:
                new_sku = f"SKU-{product.id}-{new_size}-{new_color[:3]}".upper()
            try:
                ProductVariant.objects.create(
                    product=product,
                    size=new_size,
                    color=new_color,
                    stock_qty=int(new_stock),
                    sku=new_sku
                )
                messages.success(self.request, f"Product '{product.name}' created with variant {new_size} / {new_color}!")
            except Exception as e:
                messages.warning(self.request, f"Product created, but variant could not be added: {e}")
        else:
            messages.success(self.request, f"Product '{product.name}' created successfully! Add your custom size & color variants below.")

        return response


class AdminProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    template_name = 'store/admin/product_form.html'
    fields = ['name', 'category', 'base_price', 'discount_price', 'description', 'brand', 'fabric', 'weight', 'is_active']

    def get_success_url(self):
        return reverse('store:admin_product_edit', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['variants'] = self.object.variants.all()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        product = self.object

        # 1. Handle new image uploads
        images = self.request.FILES.getlist('images')
        if images:
            start_order = product.images.count()
            for idx, img in enumerate(images):
                ProductImage.objects.create(product=product, image=img, order=start_order + idx)

        # 2. Handle image deletions if checked
        delete_image_ids = self.request.POST.getlist('delete_images')
        if delete_image_ids:
            ProductImage.objects.filter(id__in=delete_image_ids, product=product).delete()

        # 3. Handle adding a new variant (only if size, color, and stock are provided)
        new_size = self.request.POST.get('new_size', '').strip()
        new_color = self.request.POST.get('new_color', '').strip()
        new_stock = self.request.POST.get('new_stock', '').strip()
        new_sku = self.request.POST.get('new_sku', '').strip()

        if new_size and new_color and new_stock:
            existing_v = ProductVariant.objects.filter(product=product, size=new_size, color=new_color).first()
            if existing_v:
                existing_v.stock_qty = int(new_stock)
                if new_sku:
                    existing_v.sku = new_sku
                existing_v.save()
                messages.info(self.request, f"Updated stock for existing variant {new_size} / {new_color} to {new_stock}.")
            else:
                if not new_sku:
                    count = product.variants.count() + 1
                    new_sku = f"{product.slug[:6]}-{new_size}-{new_color[:3]}-{count}".upper()
                try:
                    ProductVariant.objects.create(
                        product=product,
                        size=new_size,
                        color=new_color,
                        stock_qty=int(new_stock),
                        sku=new_sku
                    )
                    messages.success(self.request, f"Added variant: {new_size} / {new_color}")
                except Exception as e:
                    messages.error(self.request, f"Could not create variant SKU '{new_sku}': {e}")

        # 4. Handle updating existing variants (size, color, stock, sku)
        for variant in product.variants.all():
            v_size_key = f"variant_size_{variant.id}"
            v_color_key = f"variant_color_{variant.id}"
            v_stock_key = f"variant_stock_{variant.id}"
            v_sku_key = f"variant_sku_{variant.id}"

            if v_size_key in self.request.POST:
                variant.size = self.request.POST.get(v_size_key, variant.size).strip()
            if v_color_key in self.request.POST:
                variant.color = self.request.POST.get(v_color_key, variant.color).strip()
            if v_stock_key in self.request.POST:
                try:
                    variant.stock_qty = int(self.request.POST.get(v_stock_key, variant.stock_qty))
                except ValueError:
                    pass
            if v_sku_key in self.request.POST and self.request.POST.get(v_sku_key):
                variant.sku = self.request.POST.get(v_sku_key).strip()

            try:
                variant.save()
            except Exception as e:
                messages.error(self.request, f"Could not update variant #{variant.id}: {e}")

        # 5. Handle deleting variant
        delete_variant_id = self.request.POST.get('delete_variant_id')
        if delete_variant_id:
            ProductVariant.objects.filter(id=delete_variant_id, product=product).delete()

        messages.success(self.request, f"Product #{product.id} updated successfully!")
        return response


class AdminProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    success_url = reverse_lazy('store:admin_products')

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        product_name = product.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Product '{product_name}' deleted successfully!")
        return response

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


# 4. Order Fulfillment Views
class AdminOrderListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = 'store/admin/order_list.html'
    context_object_name = 'orders'
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Order.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        return context


class AdminOrderDetailView(StaffRequiredMixin, DetailView):
    model = Order
    template_name = 'store/admin/order_detail.html'
    context_object_name = 'order'


def admin_order_status_update(request, pk):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        messages.error(request, "Admin access required.")
        return redirect('store:admin_login')

    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status

        shipping_partner = request.POST.get('shipping_partner', '').strip()
        tracking_number = request.POST.get('tracking_number', '').strip()

        order.shipping_partner = shipping_partner if shipping_partner else None
        order.tracking_number = tracking_number if tracking_number else None

        order.save()
        messages.success(request, f"Order #{order.id} status and shipment details updated successfully!")
    return redirect(request.META.get('HTTP_REFERER', 'store:admin_orders'))


# 5. Category Views
class AdminCategoryListView(StaffRequiredMixin, View):
    def get(self, request):
        edit_id = request.GET.get('edit')
        editing_category = None
        if edit_id:
            editing_category = Category.objects.filter(id=edit_id).first()
        categories = Category.objects.all()
        return render(request, 'store/admin/category_list.html', {
            'categories': categories,
            'editing_category': editing_category,
        })

    def post(self, request):
        category_id = request.POST.get('category_id')
        action = request.POST.get('action')

        if action == 'delete' and category_id:
            cat = get_object_or_404(Category, id=category_id)
            cat_name = cat.name
            cat.delete()
            messages.success(request, f"Category '{cat_name}' deleted.")
            return redirect('store:admin_categories')

        name = request.POST.get('name', '').strip()
        parent_id = request.POST.get('parent')
        image = request.FILES.get('image')

        parent = None
        if parent_id:
            parent = Category.objects.filter(id=parent_id).first()

        if category_id:
            cat = get_object_or_404(Category, id=category_id)
            cat.name = name
            cat.parent = parent
            if image:
                cat.image = image
            cat.save()
            messages.success(request, f"Category '{name}' updated successfully!")
        elif name:
            Category.objects.create(name=name, parent=parent, image=image)
            messages.success(request, f"Category '{name}' created successfully!")
        return redirect('store:admin_categories')


# 6. Coupon Views
class AdminCouponListView(StaffRequiredMixin, View):
    def get(self, request):
        edit_id = request.GET.get('edit')
        editing_coupon = None
        if edit_id:
            editing_coupon = Coupon.objects.filter(id=edit_id).first()
        coupons = Coupon.objects.all().order_by('-valid_from')
        return render(request, 'store/admin/coupon_list.html', {
            'coupons': coupons,
            'editing_coupon': editing_coupon,
        })

    def post(self, request):
        coupon_id = request.POST.get('coupon_id')
        action = request.POST.get('action')

        if action == 'delete' and coupon_id:
            cpn = get_object_or_404(Coupon, id=coupon_id)
            cpn_code = cpn.code
            cpn.delete()
            messages.success(request, f"Coupon '{cpn_code}' deleted.")
            return redirect('store:admin_coupons')

        if action == 'toggle' and coupon_id:
            cpn = get_object_or_404(Coupon, id=coupon_id)
            cpn.is_active = not cpn.is_active
            cpn.save()
            messages.success(request, f"Coupon '{cpn.code}' active status updated.")
            return redirect('store:admin_coupons')

        code = request.POST.get('code', '').strip().upper()
        discount_type = request.POST.get('discount_type')
        discount_value = request.POST.get('discount_value')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        is_active = request.POST.get('is_active') == 'on'

        if coupon_id:
            cpn = get_object_or_404(Coupon, id=coupon_id)
            cpn.code = code
            cpn.discount_type = discount_type
            cpn.discount_value = Decimal(discount_value)
            cpn.valid_from = valid_from
            cpn.valid_to = valid_to
            cpn.is_active = is_active
            cpn.save()
            messages.success(request, f"Coupon '{code}' updated successfully!")
        elif code and discount_value:
            Coupon.objects.create(
                code=code,
                discount_type=discount_type,
                discount_value=Decimal(discount_value),
                valid_from=valid_from,
                valid_to=valid_to,
                is_active=is_active
            )
            messages.success(request, f"Coupon '{code}' created successfully!")
        return redirect('store:admin_coupons')


# 7. Customer Review Management Views
class AdminReviewListView(StaffRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        rating_filter = request.GET.get('rating', '')

        reviews = ProductReview.objects.select_related('product', 'user').order_by('-created_at')

        if query:
            reviews = reviews.filter(
                Q(product__name__icontains=query) |
                Q(user__username__icontains=query) |
                Q(comment__icontains=query)
            )

        if rating_filter:
            try:
                reviews = reviews.filter(rating=int(rating_filter))
            except ValueError:
                pass

        # Summary Metrics
        all_reviews = ProductReview.objects.all()
        total_reviews = all_reviews.count()
        avg_rating_val = all_reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0
        avg_rating = round(avg_rating_val, 1)
        five_star_count = all_reviews.filter(rating=5).count()
        low_star_count = all_reviews.filter(rating__lte=3).count()

        return render(request, 'store/admin/review_list.html', {
            'reviews': reviews,
            'query': query,
            'rating_filter': rating_filter,
            'total_reviews': total_reviews,
            'avg_rating': avg_rating,
            'five_star_count': five_star_count,
            'low_star_count': low_star_count,
        })


class AdminReviewDeleteView(StaffRequiredMixin, DeleteView):
    model = ProductReview
    success_url = reverse_lazy('store:admin_reviews')

    def delete(self, request, *args, **kwargs):
        review = self.get_object()
        reviewer = review.user.username
        product_name = review.product.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Review by '{reviewer}' for '{product_name}' deleted successfully!")
        return response

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


# 8. Admin Banner Carousel Management Views
class AdminCarouselListView(StaffRequiredMixin, View):
    def get(self, request):
        slides = CarouselSlide.objects.all().order_by('order', '-created_at')
        return render(request, 'store/admin/carousel_list.html', {
            'slides': slides
        })

    def post(self, request):
        slide_id = request.POST.get('slide_id')
        title = request.POST.get('title', '').strip()
        subtitle = request.POST.get('subtitle', '').strip()
        description = request.POST.get('description', '').strip()
        button_text = request.POST.get('button_text', '').strip()
        button_link = request.POST.get('button_link', '').strip()
        order_val = request.POST.get('order', '0')
        is_active = request.POST.get('is_active') == 'on'
        image_file = request.FILES.get('image')

        try:
            order = int(order_val)
        except ValueError:
            order = 0

        if slide_id:
            slide = get_object_or_404(CarouselSlide, id=slide_id)
            slide.title = title
            slide.subtitle = subtitle
            slide.description = description
            slide.button_text = button_text
            slide.button_link = button_link
            slide.order = order
            slide.is_active = is_active
            if image_file:
                slide.image = image_file
            slide.save()
            messages.success(request, f"Carousel slide '{slide.title}' updated successfully!")
        else:
            if not image_file:
                messages.error(request, "An image is required when creating a new carousel slide.")
                return redirect('store:admin_carousel')
            slide = CarouselSlide.objects.create(
                title=title,
                subtitle=subtitle,
                description=description,
                image=image_file,
                button_text=button_text,
                button_link=button_link,
                order=order,
                is_active=is_active
            )
            messages.success(request, f"New Carousel slide '{slide.title}' created successfully!")
        return redirect('store:admin_carousel')


class AdminCarouselDeleteView(StaffRequiredMixin, DeleteView):
    model = CarouselSlide
    success_url = reverse_lazy('store:admin_carousel')

    def delete(self, request, *args, **kwargs):
        slide = self.get_object()
        slide_title = slide.title
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Carousel slide '{slide_title}' deleted successfully!")
        return response

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


# 9. Admin Customer User List View
from django.contrib.auth.models import User

class AdminUserListView(StaffRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        users = User.objects.filter(is_staff=False, is_superuser=False).select_related('profile').annotate(
            total_orders=Count('orders', distinct=True),
            total_spent=Sum(
                'orders__total_amount',
                filter=Q(orders__payment_status='Paid') | Q(orders__status__in=['Paid', 'Processing', 'Shipped', 'Delivered']),
                distinct=True
            )
        ).order_by('-date_joined')

        if query:
            users = users.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(profile__phone__icontains=query)
            )

        # Summary Metrics
        total_customers = User.objects.filter(is_staff=False, is_superuser=False).count()
        active_buyers_count = User.objects.filter(is_staff=False, is_superuser=False, orders__isnull=False).distinct().count()
        total_revenue_val = Order.objects.filter(
            Q(payment_status='Paid') | Q(status__in=['Paid', 'Processing', 'Shipped', 'Delivered'])
        ).aggregate(sum=Sum('total_amount'))['sum'] or Decimal('0.00')

        return render(request, 'store/admin/user_list.html', {
            'users': users,
            'query': query,
            'total_customers': total_customers,
            'active_buyers_count': active_buyers_count,
            'total_revenue_val': total_revenue_val,
        })
