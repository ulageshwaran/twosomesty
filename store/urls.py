from django.urls import path, re_path
from . import views, admin_views

app_name = 'store'

urlpatterns = [
    # General Routing
    path('', views.HomeView.as_view(), name='home'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),

    # Custom Admin Dashboard Routing (Staff Only)
    path('dashboard/login/', admin_views.AdminLoginView.as_view(), name='admin_login'),
    path('dashboard/logout/', admin_views.admin_logout, name='admin_logout'),
    path('dashboard/', admin_views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/products/', admin_views.AdminProductListView.as_view(), name='admin_products'),
    path('dashboard/products/add/', admin_views.AdminProductCreateView.as_view(), name='admin_product_add'),
    path('dashboard/products/edit/<int:pk>/', admin_views.AdminProductUpdateView.as_view(), name='admin_product_edit'),
    path('dashboard/products/delete/<int:pk>/', admin_views.AdminProductDeleteView.as_view(), name='admin_product_delete'),
    path('dashboard/orders/', admin_views.AdminOrderListView.as_view(), name='admin_orders'),
    path('dashboard/orders/<int:pk>/', admin_views.AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('dashboard/orders/<int:pk>/update-status/', admin_views.admin_order_status_update, name='admin_order_status_update'),
    path('dashboard/categories/', admin_views.AdminCategoryListView.as_view(), name='admin_categories'),
    path('dashboard/coupons/', admin_views.AdminCouponListView.as_view(), name='admin_coupons'),
    path('dashboard/reviews/', admin_views.AdminReviewListView.as_view(), name='admin_reviews'),
    path('dashboard/reviews/delete/<int:pk>/', admin_views.AdminReviewDeleteView.as_view(), name='admin_review_delete'),
    path('dashboard/carousel/', admin_views.AdminCarouselListView.as_view(), name='admin_carousel'),
    path('dashboard/carousel/delete/<int:pk>/', admin_views.AdminCarouselDeleteView.as_view(), name='admin_carousel_delete'),
    path('dashboard/users/', admin_views.AdminUserListView.as_view(), name='admin_users'),

    # Authentication Routing
    path('accounts/signup/', views.SignUpView.as_view(), name='signup'),
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', views.CustomLogoutView.as_view(), name='logout'),

    # User Profile & Addresses Routing
    path('accounts/profile/', views.ProfileView.as_view(), name='profile'),
    path('accounts/addresses/', views.AddressListView.as_view(), name='address_list'),
    path('accounts/addresses/add/', views.AddressCreateView.as_view(), name='address_add'),
    path('accounts/addresses/edit/<int:pk>/', views.AddressUpdateView.as_view(), name='address_edit'),
    path('accounts/addresses/delete/<int:pk>/', views.address_delete, name='address_delete'),
    path('accounts/addresses/default/<int:pk>/', views.address_set_default, name='address_set_default'),

    # Cart Routing
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'),
    path('cart/add/', views.cart_add_ajax, name='cart_add'),
    path('cart/update/<int:pk>/', views.cart_update_ajax, name='cart_update'),
    path('cart/remove/<int:pk>/', views.cart_remove_ajax, name='cart_remove'),
    path('cart/coupon/', views.cart_coupon_apply_ajax, name='cart_coupon_apply'),

    # Checkout & Orders Routing
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('checkout/success/<int:order_id>/', views.CheckoutSuccessView.as_view(), name='checkout_success'),
    path('checkout/razorpay-callback/', views.RazorpayCallbackView.as_view(), name='razorpay_callback'),
    path('accounts/orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('accounts/orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('accounts/orders/<int:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order_invoice'),

    # Search Routing
    path('search/', views.SearchView.as_view(), name='search'),
    path('search/suggest/', views.search_suggest_ajax, name='search_suggest'),

    # Wishlist Routing
    path('wishlist/', views.WishlistListView.as_view(), name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle_ajax, name='wishlist_toggle'),

    # Product Reviews Routing
    path('product/<slug:slug>/review/', views.ProductReviewCreateView.as_view(), name='product_add_review'),

    # Error Page Previews
    path('404/', views.custom_404_view, name='preview_404'),
    path('500/', views.custom_500_view, name='preview_500'),
    path('403/', views.custom_403_view, name='preview_403'),
    path('400/', views.custom_400_view, name='preview_400'),

    # Catch-all 404 handler for invalid URLs (excluding media and static routes)
    re_path(r'^(?!(media|static)/).*$', views.custom_404_view, name='catch_all_404'),
]
