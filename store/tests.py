from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Profile, Address, Category, Product, ProductVariant, Cart, CartItem, Coupon, Order, OrderItem, Wishlist, ProductReview
from .utils import get_or_create_cart, merge_carts

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('store:signup')
        self.login_url = reverse('store:login')
        self.profile_url = reverse('store:profile')

    def test_signup_creates_profile(self):
        """Verify that user registration automatically creates a Profile record."""
        response = self.client.post(self.signup_url, {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'phone': '9876543210',
            'password1': 'NewPass123!',
            'password2': 'NewPass123!',
        })
        self.assertEqual(response.status_code, 302) # Redirect to profile
        
        # Verify user exists
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        
        # Verify Profile exists
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.phone, '9876543210')

    def test_profile_requires_login(self):
        """Verify that profile pages are protected by authentication."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('store:login'), response.url)


class AddressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        self.address_add_url = reverse('store:address_add')
        self.address_list_url = reverse('store:address_list')

    def test_add_address_default_logic(self):
        """Verify adding addresses and that default-address toggling works correctly."""
        # 1. Add first address
        response1 = self.client.post(self.address_add_url, {
            'line1': '123 Street A',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600001',
            'is_default': True
        })
        self.assertEqual(response1.status_code, 302)
        
        addr1 = Address.objects.get(line1='123 Street A')
        self.assertTrue(addr1.is_default)

        # 2. Add second address and set it as default
        response2 = self.client.post(self.address_add_url, {
            'line1': '456 Street B',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600002',
            'is_default': True
        })
        self.assertEqual(response2.status_code, 302)
        
        # Reload both addresses
        addr1.refresh_from_db()
        addr2 = Address.objects.get(line1='456 Street B')
        
        # Verify default transferred to second address
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)


class CartMergingTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed categories, product & variant
        self.category = Category.objects.create(name='T-Shirts')
        self.product = Product.objects.create(
            name='Test Tee',
            description='Test Product description',
            category=self.category,
            base_price=100.00
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Black',
            stock_qty=10,
            sku='SKU-M-BLACK'
        )
        
        # Create user
        self.user = User.objects.create_user(username='buyer', password='password123')

    def test_cart_merge_on_login(self):
        """Verify that items added to a guest cart are successfully merged upon login."""
        # 1. Simulate guest shopping (no user login)
        # Create a session key by requesting any page
        self.client.get(reverse('store:home'))
        session = self.client.session
        session_key = session.session_key
        
        # Get or create guest cart representing this session
        guest_cart, _ = Cart.objects.get_or_create(session_key=session_key)
        CartItem.objects.create(cart=guest_cart, variant=self.variant, quantity=2)

        # 2. Log in guest user
        login_response = self.client.post(reverse('store:login'), {
            'username': 'buyer',
            'password': 'password123'
        })
        self.assertEqual(login_response.status_code, 302)

        # 3. Verify carts are merged
        # Guest cart should be deleted
        self.assertFalse(Cart.objects.filter(session_key=session_key).exists())
        
        # User cart should exist with the merged item quantity of 2
        user_cart = Cart.objects.get(user=self.user)
        user_items = CartItem.objects.filter(cart=user_cart)
        self.assertEqual(user_items.count(), 1)
        self.assertEqual(user_items.first().variant, self.variant)
        self.assertEqual(user_items.first().quantity, 2)


class CatalogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Jackets', slug='jackets')
        self.product = Product.objects.create(
            name='Warm Bomber Jacket',
            description='Test description of bomber jacket',
            category=self.category,
            base_price=2000.00
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='L',
            color='Blue',
            stock_qty=15,
            sku='SKU-L-BLUE'
        )

    def test_category_page_renders(self):
        """Verify the PLP page renders correctly with the product list."""
        url = reverse('store:category_detail', kwargs={'slug': self.category.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/category_detail.html')
        self.assertContains(response, 'Warm Bomber Jacket')

    def test_category_htmx_partial_renders(self):
        """Verify that HTMX requests only return the product grid partial."""
        url = reverse('store:category_detail', kwargs={'slug': self.category.slug})
        # Call with HTMX header
        response = self.client.get(url, headers={'HX-Request': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/partials/product_grid.html')
        self.assertTemplateNotUsed(response, 'store/base.html') # Ensure full layout is not rendered
        self.assertContains(response, 'Warm Bomber Jacket')

    def test_product_page_renders(self):
        """Verify the PDP page renders correctly with JSON variants and main details."""
        url = reverse('store:product_detail', kwargs={'slug': self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertContains(response, 'Warm Bomber Jacket')
        self.assertIn('variants_json', response.context)
        self.assertIn('SKU-L-BLUE', response.context['variants_json'])


class CartInteractivityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Shirts', slug='shirts')
        self.product = Product.objects.create(
            name='Summer Linen Shirt',
            description='Test description',
            category=self.category,
            base_price=1500.00
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='White',
            stock_qty=10,
            sku='SKU-M-WHITE'
        )
        # Create active coupon
        from django.utils import timezone
        now = timezone.now()
        self.coupon = Coupon.objects.create(
            code='DISCOUNT10',
            discount_type='P',
            discount_value=10.00,
            valid_from=now - timezone.timedelta(days=1),
            valid_to=now + timezone.timedelta(days=5),
            is_active=True
        )

    def test_cart_add_redirect(self):
        """Verify that adding items to the cart redirects to the cart detail page."""
        url = reverse('store:cart_add')
        response = self.client.post(url, {
            'variant_id': self.variant.id,
            'quantity': 2
        })
        
        self.assertRedirects(response, reverse('store:cart_detail'))
        
        # Verify database changes
        cart = Cart.objects.first()
        self.assertIsNotNone(cart)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)
        self.assertEqual(cart.subtotal, 3000.00)

    def test_cart_update_ajax(self):
        """Verify that item quantities can be updated via AJAX."""
        # Initialize session
        self.client.get(reverse('store:home'))
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        
        url = reverse('store:cart_update', kwargs={'pk': item.pk})
        response = self.client.post(url, {
            'quantity': 4
        }, headers={'HX-Request': 'true'}, HTTP_REFERER='/cart/')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/partials/cart_summary.html')
        
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_cart_remove_ajax(self):
        """Verify that items can be removed from the cart via AJAX."""
        # Initialize session
        self.client.get(reverse('store:home'))
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        
        url = reverse('store:cart_remove', kwargs={'pk': item.pk})
        response = self.client.post(url, headers={'HX-Request': 'true'})
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_coupon_apply_ajax(self):
        """Verify that active coupons can be validated and applied to the cart."""
        # Initialize session
        self.client.get(reverse('store:home'))
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2) # total subtotal: ₹3000.00
        
        url = reverse('store:cart_coupon_apply')
        response = self.client.post(url, {
            'coupon_code': 'DISCOUNT10'
        }, headers={'HX-Request': 'true'})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/partials/cart_summary.html')
        
        cart.refresh_from_db()
        self.assertEqual(cart.coupon, self.coupon)
        self.assertEqual(cart.discount_amount, 300.00) # 10% of ₹3000
        self.assertEqual(cart.total_price, 2700.00) # Free shipping. No GST.


class CheckoutAndOrderHistoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users
        self.user1 = User.objects.create_user(username='buyer1', password='password123', email='buyer1@test.com')
        self.user2 = User.objects.create_user(username='buyer2', password='password123', email='buyer2@test.com')
        
        # Create addresses
        self.addr1 = Address.objects.create(user=self.user1, line1='123 St', city='Chennai', state='Tamil Nadu', pincode='600001', is_default=True)
        self.addr2 = Address.objects.create(user=self.user2, line1='456 Ave', city='Chennai', state='Tamil Nadu', pincode='600002', is_default=True)
        
        # Create category and product
        self.category = Category.objects.create(name='T-Shirts')
        self.product = Product.objects.create(
            name='Test Tee',
            category=self.category,
            base_price=1000.00,
            is_active=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Jet Black',
            stock_qty=15,
            sku='TWS-TEST-M'
        )

    def test_checkout_requires_login(self):
        """Verify that checkout page requires authentication."""
        url = reverse('store:checkout')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_checkout_with_empty_cart(self):
        """Verify that checkout redirects back to cart if cart is empty."""
        self.client.login(username='buyer1', password='password123')
        url = reverse('store:checkout')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('store:cart_detail'))

    def test_checkout_successful_order_creation(self):
        """Verify that valid checkout submission successfully creates the order, reduces stock, and clears cart."""
        self.client.login(username='buyer1', password='password123')
        
        # Initialize user's cart in db
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=3)
        
        url = reverse('store:checkout')
        response = self.client.post(url, {
            'address_id': self.addr1.id
        })
        
        # Check order exists
        order = Order.objects.filter(user=self.user1).first()
        self.assertIsNotNone(order)
        self.assertRedirects(response, reverse('store:checkout_success', kwargs={'order_id': order.id}))
        
        # Check stock reduction: 15 - 3 = 12
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 12)
        
        # Check cart cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)
        self.assertEqual(order.status, 'Paid')
        self.assertEqual(order.payment_status, 'Paid')
        
        # Check item total sum
        self.assertEqual(order.total_amount, 3000.00) # Shipping is free. No GST.

    def test_order_detail_ownership_protection(self):
        """Verify that a user cannot view another user's order details."""
        # 1. Create order for user1
        order = Order.objects.create(
            user=self.user1,
            address=self.addr1,
            status='Paid',
            total_amount=1050.00
        )
        
        # 2. Log in as user2
        self.client.login(username='buyer2', password='password123')
        
        # 3. Request details for user1's order
        url = reverse('store:order_detail', kwargs={'pk': order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404) # Not Found / Forbidden

    def test_order_invoice_rendering(self):
        """Verify that the invoice rendering loads successfully for order owner."""
        order = Order.objects.create(
            user=self.user1,
            address=self.addr1,
            status='Paid',
            total_amount=1050.00
        )
        self.client.login(username='buyer1', password='password123')
        url = reverse('store:order_invoice', kwargs={'pk': order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/invoice.html')


class SearchWishlistAndReviewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='password123')
        
        self.category = Category.objects.create(name='Jackets')
        self.product = Product.objects.create(
            name='Windbreaker Bomber Jacket',
            category=self.category,
            base_price=2000.00,
            is_active=True,
            brand='Twosomesty'
        )

    def test_product_search_success(self):
        """Verify that searching for a keyword renders matching products."""
        url = reverse('store:search')
        response = self.client.get(url, {'q': 'Bomber'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/search.html')
        self.assertContains(response, 'Windbreaker Bomber Jacket')

    def test_autosuggest_search_success(self):
        """Verify that header autosuggest returns matching categories and products."""
        url = reverse('store:search_suggest')
        response = self.client.get(url, {'q': 'Jackets'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/partials/search_suggestions.html')
        self.assertContains(response, 'Jackets')

    def test_wishlist_list_requires_login(self):
        """Verify that guest users are redirected to login when accessing wishlist."""
        url = reverse('store:wishlist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_wishlist_toggle_adds_and_removes(self):
        """Verify that POST to wishlist toggle inserts and deletes wishlist entries."""
        self.client.login(username='tester', password='password123')
        url = reverse('store:wishlist_toggle', kwargs={'product_id': self.product.id})
        
        # 1. First click: Add to Wishlist
        response = self.client.post(url, headers={'HX-Request': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Wishlist.objects.filter(user=self.user, product=self.product).exists())
        self.assertTemplateUsed(response, 'store/partials/wishlist_button.html')
        
        # 2. Second click: Remove from Wishlist
        response = self.client.post(url, headers={'HX-Request': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Wishlist.objects.filter(user=self.user, product=self.product).exists())

    def test_review_creation_success(self):
        """Verify that submitting reviews calculates average rating and lists comment."""
        self.client.login(username='tester', password='password123')
        url = reverse('store:product_add_review', kwargs={'slug': self.product.slug})
        
        # Post a 4-star review
        response = self.client.post(url, {
            'rating': '4',
            'comment': 'Really comfortable fabric and perfect oversized fit.'
        })
        self.assertRedirects(response, reverse('store:product_detail', kwargs={'slug': self.product.slug}))
        
        # Verify counts
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviews_count, 1)
        self.assertEqual(self.product.average_rating, 4.0)
        
        review = ProductReview.objects.filter(user=self.user, product=self.product).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.comment, 'Really comfortable fabric and perfect oversized fit.')

    def test_review_unique_restriction(self):
        """Verify that posting multiple reviews for same product updates instead of duplicating."""
        self.client.login(username='tester', password='password123')
        url = reverse('store:product_add_review', kwargs={'slug': self.product.slug})
        
        # 1. Post first review (3 stars)
        self.client.post(url, {'rating': '3', 'comment': 'Okay quality'})
        
        # 2. Post second review (5 stars)
        self.client.post(url, {'rating': '5', 'comment': 'Actually it is great after wash'})
        
        self.product.refresh_from_db()
        # Count should still be 1 review
        self.assertEqual(self.product.reviews_count, 1)
        self.assertEqual(self.product.average_rating, 5.0)
        
        review = ProductReview.objects.filter(user=self.user, product=self.product).first()
        self.assertEqual(review.comment, 'Actually it is great after wash')


from django.core import mail
from unittest.mock import patch

class OrderNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer2', email='buyer2@example.com', password='password123')
        self.address = Address.objects.create(
            user=self.user,
            line1='123 Main St',
            city='Chennai',
            state='Tamil Nadu',
            pincode='600001',
            is_default=True
        )
        self.category = Category.objects.create(name='T-Shirts')
        self.product = Product.objects.create(
            name='Standard Tee',
            category=self.category,
            base_price=1000.00
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='White',
            stock_qty=10,
            sku='STD-M'
        )

    @patch('store.utils.requests.get')
    def test_order_paid_sends_notifications(self, mock_get):
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Clear outbox
        mail.outbox = []

        # Create a pending order
        order = Order.objects.create(
            user=self.user,
            address=self.address,
            status='Pending',
            total_amount=1000.00,
            payment_status='Pending'
        )

        # Create order item
        OrderItem.objects.create(
            order=order,
            variant=self.variant,
            quantity=1,
            price_at_purchase=1000.00
        )

        # Update payment_status to Paid
        order.payment_status = 'Paid'
        order.save()

        # Reload order
        order.refresh_from_db()

        # Check notification_sent is True
        self.assertTrue(order.notification_sent)

        # Check emails sent (one to buyer, one to owner)
        self.assertEqual(len(mail.outbox), 2)
        
        # Verify customer email details
        customer_email = [m for m in mail.outbox if 'buyer2@example.com' in m.to]
        self.assertEqual(len(customer_email), 1)
        self.assertIn(f"Order #{order.id}", customer_email[0].subject)
        self.assertIn("Standard Tee", customer_email[0].body)
        self.assertIn("Tamil Nadu", customer_email[0].body)

        # Verify owner email details
        owner_email = [m for m in mail.outbox if 'upmtechnologies@gmail.com' in m.to]
        self.assertEqual(len(owner_email), 1)
        self.assertIn("New Paid Order Received", owner_email[0].subject)
        self.assertIn("buyer2", owner_email[0].body)

        # Verify callmebot API was hit
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs['params']['phone'], '919342563200')
        self.assertEqual(kwargs['params']['apikey'], 'your-apikey')
        self.assertIn(f"Order ID: #{order.id}", kwargs['params']['text'])




