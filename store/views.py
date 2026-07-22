from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView, TemplateView
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import json
from .models import Address, Profile, Category, Product, ProductVariant, Cart, CartItem, Coupon, Order, OrderItem, Wishlist, ProductReview, CarouselSlide, StoreFeature
from .forms import SignUpForm, UserProfileForm, ProfileForm, AddressForm
from .utils import merge_carts, get_or_create_cart

class HomeView(TemplateView):
    template_name = 'store/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants').order_by('-created_at')[:8]
        context['carousel_slides'] = CarouselSlide.objects.filter(is_active=True)
        context['features'] = StoreFeature.objects.filter(is_active=True).order_by('order', 'id')
        return context


# Custom Sign Up View
class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'store/signup.html'
    success_url = reverse_lazy('store:profile')

    def form_valid(self, form):
        user = form.save()
        self.object = user
        # Merge guest cart to user cart before login cycles session key
        merge_carts(self.request, user)
        auth_login(self.request, user)
        return redirect(self.get_success_url())


# Custom Login View (incorporates cart merging)
class CustomLoginView(LoginView):
    template_name = 'store/login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        # Merge guest cart to user cart before login cycles session key
        merge_carts(self.request, user)
        auth_login(self.request, user)
        return redirect(self.get_success_url())


# Custom Logout View (handles both GET and POST for convenience)
class CustomLogoutView(View):
    def get(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect('store:login')

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect('store:login')


# User Profile View
class ProfileView(LoginRequiredMixin, View):
    template_name = 'store/profile.html'

    def get(self, request, *args, **kwargs):
        user_form = UserProfileForm(instance=request.user)
        # Safeguard if profile does not exist (should be created by signals)
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile_form = ProfileForm(instance=profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request, *args, **kwargs):
        profile, created = Profile.objects.get_or_create(user=request.user)
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('store:profile')

        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })


# Address Management Views
class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = 'store/address_list.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'store/address_form.html'
    success_url = reverse_lazy('store:address_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'store/address_form.html'
    success_url = reverse_lazy('store:address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    return redirect('store:address_list')


@login_required
def address_set_default(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.is_default = True
    address.save()  # Saves address. Overridden save() in Address model resets other default flags.
    return redirect('store:address_list')


# Category Listing / Product Listing Page (PLP)
class CategoryDetailView(View):
    template_name = 'store/category_detail.html'

    def get(self, request, slug, *args, **kwargs):
        category = get_object_or_404(Category, slug=slug)
        products = Product.objects.filter(category=category, is_active=True).select_related('category').prefetch_related('images', 'variants')



        # 2. Filter by Size
        size = request.GET.get('size')
        if size:
            products = products.filter(variants__size=size).distinct()

        # 3. Filter by Color
        color = request.GET.get('color')
        if color:
            products = products.filter(variants__color=color).distinct()

        # 4. Filter by Price Range
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            try:
                products = products.filter(base_price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                products = products.filter(base_price__lte=float(max_price))
            except ValueError:
                pass

        # 5. Sorting Options
        sort = request.GET.get('sort', 'newest')
        if sort == 'price_asc':
            products = products.order_by('base_price')
        elif sort == 'price_desc':
            products = products.order_by('-base_price')
        elif sort == 'newest':
            products = products.order_by('-created_at')
        else:
            # Default sorting by ID desc
            products = products.order_by('-id')

        # Dynamically fetch available options from this category for filters
        all_variants = ProductVariant.objects.filter(product__category=category)
        available_sizes = sorted(list(set(all_variants.values_list('size', flat=True))))
        available_colors = sorted(list(set(all_variants.values_list('color', flat=True))))

        # Paginate: 10 products per page
        paginator = Paginator(products, 12)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        context = {
            'category': category,
            'products': page_obj,
            'page_obj': page_obj,
            'sizes': available_sizes,
            'colors': available_colors,
            'selected_size': size,
            'selected_color': color,
            'selected_min_price': min_price,
            'selected_max_price': max_price,
            'selected_sort': sort,
        }

        # HTMX partial rendering support
        if request.headers.get('HX-Request'):
            return render(request, 'store/partials/product_grid.html', context)
        return render(request, self.template_name, context)


# Product Detail Page (PDP)
class ProductDetailView(View):
    template_name = 'store/product_detail.html'

    def get(self, request, slug, *args, **kwargs):
        product = get_object_or_404(Product.objects.select_related('category').prefetch_related('images', 'variants'), slug=slug, is_active=True)
        variants = product.variants.all()

        # Serialize variant options to JSON for Alpine.js component
        variants_data = []
        for v in variants:
            variants_data.append({
                'id': v.id,
                'size': v.size,
                'color': v.color,
                'stock': v.stock_qty,
                'price': float(v.price),
                'sku': v.sku
            })

        # Extract unique sizes and colors in standard order
        unique_sizes_raw = list(set(variants.values_list('size', flat=True)))
        size_order = {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, 'XXXL': 7}
        unique_sizes = sorted(unique_sizes_raw, key=lambda s: size_order.get(s.upper(), 99))
        
        unique_colors = sorted(list(set(variants.values_list('color', flat=True))))

        related_products = Product.objects.filter(
            category=product.category,
            is_active=True
        ).select_related('category').prefetch_related('images', 'variants').exclude(id=product.id)[:4]

        # Fallback to other categories if fewer than 4 related products are found
        related_count = related_products.count()
        if related_count < 4:
            already_included = list(related_products.values_list('id', flat=True)) + [product.id]
            additional_products = Product.objects.filter(is_active=True).exclude(id__in=already_included)[:4 - related_count]
            related_products = list(related_products) + list(additional_products)

        context = {
            'product': product,
            'variants': variants,
            'variants_json': json.dumps(variants_data),
            'related_products': related_products,
            'sizes': unique_sizes,
            'colors': unique_colors,
        }
        return render(request, self.template_name, context)


# Cart Page View
class CartDetailView(TemplateView):
    template_name = 'store/cart_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_or_create_cart(self.request)
        context['cart'] = cart
        return context


@require_POST
def cart_add_ajax(request):
    cart = get_or_create_cart(request)
    variant_id = request.POST.get('variant_id')
    qty = int(request.POST.get('quantity', 1))
    
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # Check/Create CartItem
    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    if not created:
        item.quantity += qty
    else:
        item.quantity = qty
        
    # Limit to available stock
    if item.quantity > variant.stock_qty:
        item.quantity = variant.stock_qty
        
    if item.quantity <= 0:
        item.delete()
    else:
        item.save()
        
    # Recalculate cart count
    cart_count = sum(i.quantity for i in cart.items.all())
    
    # Check if HTMX request
    if request.headers.get('HX-Request') == 'true':
        # Render the updated cart drawer list
        context = {'cart': cart, 'cart_count': cart_count}
        response_html = render_to_string('store/partials/cart_drawer_content.html', context, request=request)
        return HttpResponse(response_html)
        
    return redirect('store:cart_detail')


@require_POST
def cart_update_ajax(request, pk):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    qty = int(request.POST.get('quantity', 1))
    
    if qty <= 0:
        item.delete()
    else:
        # Cap at stock_qty
        if qty > item.variant.stock_qty:
            qty = item.variant.stock_qty
        item.quantity = qty
        item.save()
        
    cart_count = sum(i.quantity for i in cart.items.all())
    
    if request.headers.get('HX-Request') == 'true':
        # Check if requested from the main /cart/ page or the drawer
        referer = request.headers.get('Referer', '')
        if '/cart/' in referer:
            context = {'cart': cart, 'cart_count': cart_count}
            response_html = render_to_string('store/partials/cart_summary.html', context, request=request)
            return HttpResponse(response_html)
        else:
            context = {'cart': cart, 'cart_count': cart_count}
            response_html = render_to_string('store/partials/cart_drawer_content.html', context, request=request)
            return HttpResponse(response_html)
            
    return redirect('store:cart_detail')


@require_POST
def cart_remove_ajax(request, pk):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    item.delete()
    
    cart_count = sum(i.quantity for i in cart.items.all())
    
    if request.headers.get('HX-Request') == 'true':
        referer = request.headers.get('Referer', '')
        if '/cart/' in referer:
            context = {'cart': cart, 'cart_count': cart_count}
            response_html = render_to_string('store/partials/cart_summary.html', context, request=request)
            return HttpResponse(response_html)
        else:
            context = {'cart': cart, 'cart_count': cart_count}
            response_html = render_to_string('store/partials/cart_drawer_content.html', context, request=request)
            return HttpResponse(response_html)
            
    return redirect('store:cart_detail')


@require_POST
def cart_coupon_apply_ajax(request):
    cart = get_or_create_cart(request)
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    
    from django.utils import timezone
    now = timezone.now()
    error_msg = None
    
    if not coupon_code:
        cart.coupon = None
        cart.save()
    else:
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            if coupon.valid_from <= now <= coupon.valid_to:
                cart.coupon = coupon
                cart.save()
            else:
                error_msg = "This coupon code is expired."
                cart.coupon = None
                cart.save()
        except Coupon.DoesNotExist:
            error_msg = "Invalid coupon code."
            cart.coupon = None
            cart.save()
            
    cart_count = sum(i.quantity for i in cart.items.all())
    
    if request.headers.get('HX-Request') == 'true':
        context = {
            'cart': cart, 
            'cart_count': cart_count, 
            'coupon_error': error_msg,
            'coupon_success': "Coupon applied successfully!" if not error_msg and coupon_code else None
        }
        response_html = render_to_string('store/partials/cart_summary.html', context, request=request)
        return HttpResponse(response_html)
        
    return redirect('store:cart_detail')


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            return redirect('store:cart_detail')
        
        addresses = request.user.addresses.all()
        address_form = AddressForm()
        
        # Count jackets in cart
        jackets_count = sum(item.quantity for item in cart.items.all() if item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
        
        context = {
            'cart': cart,
            'addresses': addresses,
            'address_form': address_form,
            'jackets_count': jackets_count,
        }
        
        if request.GET.get('payment_cancelled') == 'true':
            context['error'] = 'Payment was cancelled. You can retry placing your order now.'
            
        return render(request, 'store/checkout.html', context)

    def post(self, request):
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            return redirect('store:cart_detail')

        address_id = request.POST.get('address_id')
        address = None

        if address_id == 'new':
            form = AddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                address.save()
            else:
                addresses = request.user.addresses.all()
                jackets_count = sum(item.quantity for item in cart.items.all() if item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
                context = {
                    'cart': cart,
                    'addresses': addresses,
                    'address_form': form,
                    'jackets_count': jackets_count,
                }
                return render(request, 'store/checkout.html', context)
        elif address_id:
            try:
                address = Address.objects.get(pk=address_id, user=request.user)
            except Address.DoesNotExist:
                pass

        if not address:
            addresses = request.user.addresses.all()
            address_form = AddressForm()
            jackets_count = sum(item.quantity for item in cart.items.all() if item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
            context = {
                'cart': cart,
                'addresses': addresses,
                'address_form': address_form,
                'jackets_count': jackets_count,
                'error': 'Please select or enter a valid shipping address.'
            }
            return render(request, 'store/checkout.html', context)

        # Calculate shipping amount and order total dynamically based on shipping address state and jacket count
        from decimal import Decimal
        sub = cart.subtotal
        disc = cart.discount_amount
        net = sub - disc
        
        # Count jackets
        jacket_qty = sum(item.quantity for item in cart.items.all() if item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
        
        state_lower = address.state.strip().lower() if address and address.state else ''
        is_tn = state_lower in ['tamil nadu', 'tamilnadu', 'tn']
        
        if jacket_qty >= 3:
            shipping_amount = Decimal('100.00') if is_tn else Decimal('200.00')
        else:
            shipping_amount = Decimal('50.00') if is_tn else Decimal('100.00')
            
        order_total = net + shipping_amount

        # Create Order in Pending status initially
        order = Order.objects.create(
            user=request.user,
            address=address,
            status='Pending',
            total_amount=order_total,
            coupon_applied=cart.coupon,
            payment_status='Pending'
        )

        # Create Order Items (but do not decrease stock or clear cart yet)
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price_at_purchase=item.variant.price
            )

        # Create Razorpay Order
        # pyrefly: ignore [missing-import]
        import razorpay
        from django.conf import settings
        
        try:
            key_id = settings.RAZORPAY_KEY_ID.strip() if settings.RAZORPAY_KEY_ID else ''
            key_secret = settings.RAZORPAY_KEY_SECRET.strip() if settings.RAZORPAY_KEY_SECRET else ''
            
            if not key_id or not key_secret:
                raise ValueError("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET is missing in .env")
                
            client = razorpay.Client(auth=(key_id, key_secret))
            
            razorpay_order = client.order.create(data={
                "amount": int(order_total * 100),  # Amount in paise
                "currency": "INR",
                "receipt": f"receipt_order_{order.id}",
            })
            
            order.razorpay_order_id = razorpay_order['id']
            order.save()
        except Exception as e:
            order.status = 'Cancelled'
            order.payment_status = 'Failed'
            order.save()
            
            addresses = request.user.addresses.all()
            address_form = AddressForm()
            jackets_count = sum(item.quantity for item in cart.items.all() if item.variant.product.category and item.variant.product.category.name.strip().lower() in ['jackets', 'jacket'])
            
            context = {
                'cart': cart,
                'addresses': addresses,
                'address_form': address_form,
                'jackets_count': jackets_count,
                'error': f'Razorpay Error: Authentication failed ({str(e)}). Please check RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file and restart your Django server.'
            }
            return render(request, 'store/checkout.html', context)

        # Render complete payment window with Razorpay SDK script
        customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        callback_url = request.build_absolute_uri(reverse('store:razorpay_callback')) + f"?order_id={order.id}"
        context = {
            'order_id': order.id,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID.strip() if settings.RAZORPAY_KEY_ID else '',
            'amount': int(order_total * 100),
            'customer_name': customer_name,
            'customer_email': request.user.email,
            'customer_phone': address.phone if address.phone else '',
            'callback_url': callback_url,
        }
        return render(request, 'store/checkout_payment.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayCallbackView(View):
    def post(self, request):
        # pyrefly: ignore [missing-import]
        import razorpay
        from django.conf import settings
        
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        order_id = request.POST.get('order_id') or request.GET.get('order_id')
        
        if not order_id:
            try:
                if request.user.is_authenticated:
                    order = Order.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
                else:
                    order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                order_id = order.id
            except Order.DoesNotExist:
                return redirect('store:checkout')
        else:
            if request.user.is_authenticated:
                order = get_object_or_404(Order, id=order_id, user=request.user)
            else:
                order = get_object_or_404(Order, id=order_id)
        
        key_id = settings.RAZORPAY_KEY_ID.strip() if settings.RAZORPAY_KEY_ID else ''
        key_secret = settings.RAZORPAY_KEY_SECRET.strip() if settings.RAZORPAY_KEY_SECRET else ''
        client = razorpay.Client(auth=(key_id, key_secret))
        
        try:
            # Verify payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            
            # Signature verification successful, finalize order status
            order.status = 'Paid'
            order.payment_status = 'Paid'
            order.razorpay_order_id = razorpay_order_id
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save()
            
            # Decrease stock for order items now that payment is confirmed
            for item in order.items.all():
                if item.variant:
                    if item.variant.stock_qty >= item.quantity:
                        item.variant.stock_qty -= item.quantity
                    else:
                        item.variant.stock_qty = 0
                    item.variant.save()
                    
            # Clear user's cart
            if order.user:
                cart = Cart.objects.filter(user=order.user).first()
            else:
                cart = get_or_create_cart(request)
            if cart:
                cart.items.all().delete()
                cart.coupon = None
                cart.save()
            
            # Send notifications
            from .utils import send_order_notifications
            send_order_notifications(order, request=request)
            
            return redirect('store:checkout_success', order_id=order.id)
            
        except Exception as e:
            order.status = 'Cancelled'
            order.payment_status = 'Failed'
            order.save()
            
            return redirect(f"{reverse('store:checkout')}?payment_cancelled=true")


class CheckoutSuccessView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'store/checkout_success.html', {'order': order})


class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'store/order_history.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        return render(request, 'store/order_detail.html', {'order': order})


class OrderInvoiceView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        if order.status in ['Cancelled', 'Failed'] or order.payment_status == 'Failed':
            messages.error(request, "Invoices cannot be generated for cancelled or failed orders.")
            return redirect('store:order_detail', pk=order.id)
        return render(request, 'store/invoice.html', {'order': order})


from django.db.models import Q

class SearchView(View):
    template_name = 'store/search.html'

    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants')

        if q:
            products = products.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q) |
                Q(brand__icontains=q) |
                Q(category__name__icontains=q)
            ).distinct()
        else:
            products = Product.objects.none()



        # 2. Filter by Size
        size = request.GET.get('size')
        if size:
            products = products.filter(variants__size=size).distinct()

        # 3. Filter by Color
        color = request.GET.get('color')
        if color:
            products = products.filter(variants__color=color).distinct()

        # 4. Filter by Price Range
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            try:
                products = products.filter(base_price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                products = products.filter(base_price__lte=float(max_price))
            except ValueError:
                pass

        # 5. Sorting Options
        sort = request.GET.get('sort', 'newest')
        if sort == 'price_asc':
            products = products.order_by('base_price')
        elif sort == 'price_desc':
            products = products.order_by('-base_price')
        elif sort == 'newest':
            products = products.order_by('-created_at')
        else:
            products = products.order_by('-id')

        # Fetch available options from these matching products
        if q:
            all_variants = ProductVariant.objects.filter(product__in=Product.objects.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q) |
                Q(brand__icontains=q) |
                Q(category__name__icontains=q)
            ).filter(is_active=True))
            available_sizes = sorted(list(set(all_variants.values_list('size', flat=True))))
            available_colors = sorted(list(set(all_variants.values_list('color', flat=True))))
        else:
            available_sizes = []
            available_colors = []

        context = {
            'q': q,
            'products': products,
            'sizes': available_sizes,
            'colors': available_colors,
            'selected_size': size,
            'selected_color': color,
            'selected_min_price': min_price,
            'selected_max_price': max_price,
            'selected_sort': sort,
        }

        if request.headers.get('HX-Request'):
            return render(request, 'store/partials/product_grid.html', context)
        return render(request, self.template_name, context)


def search_suggest_ajax(request):
    q = request.GET.get('q', '').strip()
    categories = Category.objects.none()
    products = Product.objects.none()

    if q and len(q) >= 2:
        categories = Category.objects.filter(name__icontains=q)[:3]
        products = Product.objects.filter(is_active=True).filter(
            Q(name__icontains=q) | Q(brand__icontains=q)
        )[:5]

    context = {
        'q': q,
        'categories': categories,
        'products': products,
    }
    return render(request, 'store/partials/search_suggestions.html', context)


class WishlistListView(LoginRequiredMixin, ListView):
    model = Wishlist
    template_name = 'store/wishlist.html'
    context_object_name = 'wishlist_items'

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')


@login_required
@require_POST
def wishlist_toggle_ajax(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product)
    
    if wishlist_item.exists():
        wishlist_item.delete()
        is_wishlisted = False
    else:
        Wishlist.objects.create(user=request.user, product=product)
        is_wishlisted = True

    if request.headers.get('HX-Request') == 'true':
        context = {
            'product': product,
            'is_wishlisted': is_wishlisted,
        }
        return render(request, 'store/partials/wishlist_button.html', context)

    return redirect(request.META.get('HTTP_REFERER', 'store:home'))


class ProductReviewCreateView(LoginRequiredMixin, View):
    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        rating_val = request.POST.get('rating')
        comment_val = request.POST.get('comment', '').strip()

        try:
            rating = int(rating_val)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            return redirect('store:product_detail', slug=product.slug)

        ProductReview.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'rating': rating, 'comment': comment_val}
        )
        return redirect('store:product_detail', slug=product.slug)


# Custom Error Handlers
def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)

def custom_500_view(request, exception=None):
    return render(request, '500.html', status=500)

def custom_403_view(request, exception=None):
    return render(request, '403.html', status=403)

def custom_400_view(request, exception=None):
    return render(request, '400.html', status=400)

