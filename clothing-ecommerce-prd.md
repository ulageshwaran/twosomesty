# Clothing Brand E-Commerce Website
### Product Requirements Document, Tech Stack & Design Doc

---

## 1. PRODUCT REQUIREMENTS DOCUMENT (PRD)

### 1.1 Overview
A direct-to-consumer clothing brand e-commerce website where customers can browse products by category, view detailed product pages, manage a cart, check out securely via Cashfree, and manage their account/order history. Store operations (products, categories, inventory, orders) are managed through the Django Admin panel — no separate custom admin dashboard needed initially.

### 1.2 Goals
- Fast, modern, mobile-first shopping experience.
- Smooth, app-like interactivity (add to cart, filters, quantity/size changes) without a heavy full SPA rebuild.
- Secure, reliable checkout using Cashfree.
- Low operational overhead — Django Admin is the single source of truth for catalog/order management.

### 1.3 Target Users
- End customers (guests + registered users) browsing and buying clothes.
- Store owner/admin managing products, stock, and orders via Django Admin.

### 1.4 Core Pages & Features

| Page | Key Features |
|---|---|
| **Home** | Hero banner/carousel, featured collections, new arrivals, trending products, category shortcuts, newsletter signup, footer |
| **Category (Listing/PLP)** | One page per category (T-Shirts, Jackets, Jeans, Hoodies, Oversized Tees, + any you add), each listing that category's products in a grid; filters (size, color, price, gender), sort (price, newest, popularity), pagination/infinite scroll, quick-view, wishlist toggle |
| **Product Detail (PDP)** | Opens when a product card is clicked from the category grid; shows image gallery/zoom, size & color selector, stock status, price (+ discount), add to cart, add to wishlist, description/specs/size chart tabs, related products, reviews |
| **Cart** | Line items with image/size/qty, quantity update, remove item, price breakdown (subtotal, discount, shipping, tax, total), coupon code input, proceed to checkout |
| **Checkout / Payment** | Address selection/entry, order summary, Cashfree payment integration, payment status handling (success/failure/pending) |
| **Login / Signup / Logout** | Email or phone login, JWT/session-based auth, signup, forgot password, logout |
| **User Profile** | View/edit name, email, phone, saved addresses, change password |
| **Order History** | List of past orders, order status (placed/shipped/delivered/cancelled), order detail view, invoice download, reorder |
| **Search** | Global product search bar in header, live autosuggest (HTMX, results-as-you-type), dedicated `/search/?q=` results page with same grid/filter layout as category page |
| **Wishlist** *(recommended addition)* | Saved products for later |

**Category → Product flow:** Home/Nav → user picks a category (e.g. Hoodies) → Category page lists all products in that category as a grid → user clicks a product card → Product Detail page opens showing full info (images, price, sizes, description, stock, reviews) for that single product.

**Initial categories (seed data):** T-Shirts, Jackets, Jeans, Hoodies, Oversized Tees *(structured as a `Category` model so you can add/rename/remove categories anytime from Django Admin without code changes)*.

### 1.5 User Stories (sample)
- As a visitor, I can browse products by category without logging in.
- As a visitor, I can add items to my cart as a guest; cart persists after I log in.
- As a user, I can select size/color and see live stock availability before adding to cart.
- As a user, I can pay securely via UPI/card/netbanking through Cashfree and get instant order confirmation.
- As a user, I can view my past orders and their current status.
- As an admin, I can add/edit products, manage stock, and view/update orders from Django Admin.

### 1.6 Functional Requirements
- Product catalog with categories, subcategories, variants (size/color), images, pricing, stock.
- Cart logic (guest cart via session, merges into user cart on login).
- Order creation only after successful/verified Cashfree payment (server-side verification via webhook).
- Auth: signup/login/logout, password reset, session or token-based.
- Address book per user (multiple shipping addresses).
- Order status lifecycle: `Pending → Paid → Processing → Shipped → Delivered → Cancelled/Refunded`.
- Admin manages everything through Django Admin (custom `list_display`, filters, inline order items).
- Site-wide product search with live autosuggest and a full results page.
- SEO-controllable fields (meta title/description, image alt text) editable per product/category from Django Admin — see Section 4 for full local SEO strategy.

### 1.7 Non-Functional Requirements
- Mobile-first responsive design (60%+ traffic expected on mobile for fashion e-commerce).
- Page load < 2.5s on 4G for PLP/PDP.
- HTTPS everywhere; PCI-safe payment flow (Cashfree hosted checkout — no card data touches your server).
- SEO-friendly product/category URLs (Django templates render server-side, good for SEO by default).
- Scalable data model (SQLite fine for MVP/dev; plan Postgres migration path for production scale).

### 1.8 Out of Scope (v1)
- Multi-vendor marketplace features.
- Native mobile app.
- Multi-currency/international shipping.

---

## 2. TECH STACK

### 2.1 Backend
- **Framework:** Django (Python)
- **API layer:** Django REST Framework (DRF) — even if you render most pages server-side, you'll want JSON endpoints for cart actions, filters, and Cashfree webhook handling.
- **Database:** SQLite for development. *(Recommendation: switch to PostgreSQL before production — SQLite doesn't handle concurrent writes well, which matters for orders/payments. Migration is trivial since Django's ORM abstracts the DB.)*
- **Auth:** Django's built-in auth system + `django-allauth` (optional, for email/social login) or plain session auth. Use `djangorestframework-simplejwt` only if frontend is a separate SPA calling APIs.
- **Admin:** Django Admin (built-in) — customize with `list_display`, `list_filter`, `search_fields`, inlines for order items/product variants.
- **Payments:** Cashfree Payment Gateway (Orders API + webhook verification).
- **Media storage:** Local `MEDIA_ROOT` for dev; move to S3/Cloudinary for production product images.
- **Task queue (recommended):** Celery + Redis for sending order confirmation emails, invoice generation, stock alerts (can be added post-MVP).

### 2.2 Frontend — Confirmed Approach: Django Templates + Tailwind CSS + Alpine.js + HTMX

- **Django Templates** — server-rendered HTML, great for SEO (critical since local SEO for Chennai/Tamil Nadu is a core requirement — see Section 5), no API duplication for content pages (Home, PLP, PDP).
- **Tailwind CSS** — utility-first CSS for a modern, custom dark-theme UI fast, without fighting a component library's default look.
- **Alpine.js** — lightweight (~15KB) JS for interactive bits: image gallery, size/color selectors, dropdowns, modals, quantity steppers, toasts — no build step needed.
- **HTMX** — for partial page updates without full reloads: add-to-cart, cart quantity changes, filter/sort on PLP, live search-as-you-type — all without writing a separate JSON API for every UI action.
- **Why this combo:** app-like, interactive feel (no full page reloads for cart/filter/search actions) while keeping Django as the single stack — one codebase, one deployment, server-rendered pages that are fully crawlable by Google out of the box, and no CORS/auth-token complexity between a separate frontend and backend.

### 2.3 Payment Integration
- **Cashfree Payment Gateway** — Orders API (create order → get `payment_session_id` → Cashfree Checkout (hosted/drop-in) → redirect/webhook → verify signature server-side → mark order as Paid.
- Always verify payment status server-side via Cashfree's webhook + order status API before confirming the order — never trust only the client-side redirect.
- Use Cashfree **sandbox** credentials during development, switch to production keys at launch.

### 2.4 Full Stack Summary

| Layer | Technology |
|---|---|
| Backend framework | Django |
| API (for cart/AJAX/webhooks) | Django REST Framework |
| Database (dev) | SQLite → PostgreSQL (production) |
| Templating | Django Templates |
| CSS | Tailwind CSS |
| Interactivity | Alpine.js + HTMX |
| Admin | Django Admin (customized) |
| Payments | Cashfree Payment Gateway |
| Auth | Django Auth (sessions) |
| Media/Images | Local (dev) → AWS S3 / Cloudinary (prod) |
| Background jobs (optional) | Celery + Redis |
| Deployment | Gunicorn + Nginx, or Railway/Render for quick hosting |

---

## 3. DESIGN DOCUMENT

### 3.1 Design Principles
- **Minimal, product-first UI** — let product photography lead; UI chrome stays quiet.
- **Consistent spacing scale** (Tailwind default: 4px increments) for visual rhythm.
- **Micro-interactions** — hover states, smooth add-to-cart feedback (slide-in mini cart or toast), skeleton loaders for images.
- **Mobile-first** — design for 375px width first, scale up.

### 3.2 Visual Style Guide (starting point — customize to brand identity)

**Colors — Dark Theme Palette**

| Purpose | Color Name | Hex | Usage |
|---|---|---|---|
| Main background | Deep Charcoal | `#0B0F14` | Page background |
| Secondary background | Dark Slate | `#111827` | Header/footer, section backgrounds |
| Cards / Product boxes | Elevated Slate | `#1A2230` | Product cards, modals, drawers |
| **Primary brand** | **Electric Blue** | **`#087BFF`** | CTAs, buttons, links, active states |
| **Primary hover** | **Bright Cyan Blue** | **`#20CFFF`** | Button/link hover states |
| Accent / Offers | Neon Pink | `#FF20D6` | Sale badges, discount tags, promo highlights |
| Main text | Soft White | `#F8FAFC` | Headings, primary body text |
| Secondary text | Cool Gray | `#94A3B8` | Descriptions, captions, metadata |
| Borders | Slate Gray | `#2D3748` | Dividers, input borders, card outlines |
| Success | Emerald | `#10B981` | Order confirmed, in-stock, payment success |
| Warning | Amber | `#F59E0B` | Low stock, pending payment |
| Error | Coral Red | `#F43F5E` | Out of stock, payment failed, form errors |

**Tailwind config tip:** add these as custom colors in `tailwind.config.js` (e.g. `brand.DEFAULT: '#087BFF'`, `brand.hover: '#20CFFF'`, `surface.bg: '#0B0F14'`, `surface.card: '#1A2230'`) so you reference `bg-surface-card`, `text-brand`, `hover:text-brand-hover` etc. consistently instead of hardcoding hex values across templates.

**Contrast note:** on this dark palette, use Electric Blue (`#087BFF`) sparingly for primary CTAs against the dark backgrounds — it has strong contrast against `#0B0F14`/`#1A2230`. Neon Pink (`#FF20D6`) should stay reserved for sale/offer badges only, so it doesn't compete visually with the primary brand color.

**Typography**
- Headings: a clean sans-serif (e.g. "Poppins", "Sora", or "General Sans") — bold weights for hero/product titles.
- Body: "Inter" or system-ui for readability at small sizes.
- Scale: 12 / 14 / 16 / 20 / 24 / 32 / 48px.

**Components to build once, reuse everywhere**
- Product Card (image, name, price, hover-swap image, quick add-to-cart)
- Button (primary/secondary/ghost)
- Input/Select (with focus + error states)
- Badge (Sale, New, Out of Stock)
- Modal/Drawer (used for cart drawer, quick view, filters on mobile)
- Toast/notification (add-to-cart confirmation)
- Star rating component

### 3.3 Page-Level Design Notes

**Home**
- Full-width hero (image/video) with CTA → category or collection.
- Horizontal scroll or grid for "New Arrivals" / "Best Sellers."
- Category tiles (image + label) linking to PLPs.
- Sticky header with logo, nav, search icon, cart icon (with item count badge), account icon.

**Category Page (PLP)**
- Left sidebar filters (desktop) / bottom-sheet filters (mobile): size, color, price range, sort.
- Grid: 2 columns mobile, 3–4 columns desktop.
- HTMX-powered filtering/sorting — updates grid without full page reload.
- Infinite scroll or "Load More" button.

**Product Page (PDP)**
- Left: image gallery (thumbnails + main image, zoom on hover/tap).
- Right: title, price, size selector (Alpine.js state), color swatches, stock indicator, Add to Cart (sticky on mobile scroll), Add to Wishlist.
- Below: tabs for Description / Size Chart / Reviews.
- Bottom: "You may also like" carousel.

**Cart Page / Drawer**
- Slide-in drawer (Alpine.js) for quick cart access + full cart page for review.
- Editable quantity, remove item, live subtotal update via HTMX (no full reload).
- Coupon code field with inline validation feedback.
- Clear "Proceed to Checkout" CTA, sticky on mobile.

**Checkout / Payment**
- Step layout: Address → Review Order → Payment.
- Address form with saved-address quick select for logged-in users.
- Order summary sidebar (sticky on desktop).
- Cashfree Checkout embedded/redirect at final step.
- Payment status page: Success (order confirmation + order number), Failure (retry option), Pending (auto-refresh/check status).

**Login / Signup**
- Simple centered card layout, minimal fields.
- Clear error states (inline, not just top banner).
- "Continue as Guest" option for checkout if you want to reduce friction.

**User Profile**
- Tabs or sidebar: Profile Info, Addresses, Order History, Change Password.
- Editable fields inline or via modal.

**Order History**
- List view: order ID, date, total, status badge, "View Details" link.
- Order detail: items ordered, shipping address, payment status, tracking info (if integrated), invoice download (PDF).

**Search**
- Search icon in header expands into a full-width input (or dedicated bar on mobile).
- As the user types, HTMX fires a debounced request (e.g. 300ms) to `/search/suggest/` and renders a dropdown of matching products (thumbnail, name, price) + matching categories.
- Pressing Enter or "View all results" goes to `/search/?q=...` — a full results page reusing the same grid/filter/sort layout as the Category page.
- Empty-state and "no results" messaging with suggested categories as fallback.

### 3.4 Data Model (Django Models — core structure)

```
User (Django built-in) 
 └── Profile (OneToOne: phone, avatar)
 └── Address (FK to User: line1, line2, city, state, pincode, is_default)

Category (name, slug, parent [self-FK for subcategories], image)

Product 
 ├── name, slug, description, category (FK), base_price, discount_price
 ├── gender (M/F/Unisex), brand, is_active
 └── ProductImage (FK: image, alt_text, order)
 └── ProductVariant (FK: size, color, stock_qty, sku, price_override)

Cart (FK to User [nullable for guest via session_key])
 └── CartItem (FK to Cart, FK to ProductVariant, quantity)

Order 
 ├── user (FK), address (FK), status, total_amount, coupon_applied
 ├── cashfree_order_id, payment_status, created_at
 └── OrderItem (FK to Order, FK to ProductVariant, quantity, price_at_purchase)

Coupon (code, discount_type, discount_value, valid_from, valid_to, is_active)

Wishlist (FK to User, FK to Product) [optional v1 addition]
```

### 3.5 URL Structure (example)

```
/                                → Home
/category/<slug>/                → Category/PLP
/product/<slug>/                 → Product Detail
/cart/                           → Cart page
/checkout/                       → Address + review
/checkout/payment/                → Cashfree redirect/session
/checkout/payment/callback/       → Cashfree webhook/return handler
/accounts/login/  /accounts/logout/  /accounts/signup/
/accounts/profile/
/accounts/orders/                → Order history
/accounts/orders/<id>/           → Order detail
/admin/                          → Django Admin
```

### 3.6 Cashfree Payment Flow

```
1. User clicks "Pay Now" on Checkout page
2. Django view creates a local Order (status=Pending)
3. Django backend calls Cashfree "Create Order" API → gets payment_session_id
4. Frontend loads Cashfree Checkout (Drop-in/Hosted) using payment_session_id
5. User completes payment on Cashfree UI
6. Cashfree redirects user to your return_url (show "Verifying payment...")
7. Cashfree also sends a server-to-server Webhook → your webhook view
8. Webhook handler verifies signature → checks payment status via Cashfree API
9. On success: Order.status = Paid, reduce stock, send confirmation email
10. On failure: Order.status = Failed, show retry option
   (Always trust the webhook + status API over the redirect alone)
```

---

## 4. SEO STRATEGY — TARGETING CHENNAI, TAMIL NADU

Since Django Templates render server-side, you already have a strong SEO foundation (fully crawlable HTML, no client-side rendering gap). Below is what to add specifically for local/location-based ranking in Chennai and Tamil Nadu.

### 4.1 On-Page SEO (technical)
- **Title tags & meta descriptions per page type** — dynamically generated from product/category data, with location keywords woven in naturally:
  - Home: `Clothing Brand Name | Trendy Streetwear & Fashion in Chennai, Tamil Nadu`
  - Category: `Buy Hoodies Online in Chennai | [Brand Name]`
  - Product: `[Product Name] – Buy Online in Chennai, Tamil Nadu | [Brand Name]`
- **Header tags (H1/H2)** — one H1 per page (product/category name), use H2s for sections; include "Chennai" / "Tamil Nadu" naturally in category descriptions, not stuffed into headings.
- **Semantic URLs:** `/category/hoodies/`, `/product/oversized-black-hoodie/` — avoid IDs/query strings in URLs.
- **Image SEO:** descriptive `alt` text for every product image (e.g. `"Black oversized hoodie – streetwear Chennai"`), compressed images (WebP), lazy-loading below the fold.
- **Canonical tags** on filtered/sorted PLP URLs to avoid duplicate-content issues from filter combinations.
- **Mobile-first & Core Web Vitals:** optimize LCP/CLS — critical since Google uses mobile-first indexing and page experience as ranking signals.

### 4.2 Structured Data (Schema.org / JSON-LD)
Add these via Django template blocks so every page auto-generates the right schema:
- **`Product` schema** on PDP — name, image, price, availability, brand, aggregateRating (once reviews exist).
- **`BreadcrumbList` schema** — Home → Category → Product breadcrumb trail (also improves UX).
- **`LocalBusiness` / `ClothingStore` schema** on Home/About/Contact — include `address` (with `addressLocality: Chennai`, `addressRegion: Tamil Nadu`), `geo` coordinates, `openingHours`, `telephone`.
- **`Organization` schema** with logo, social profiles, and contact info.

### 4.3 Local SEO Specifics (Chennai / Tamil Nadu)
- **Google Business Profile:** create/verify a listing for the brand (even for an online store with a Chennai base/warehouse/office) — category "Clothing store," service area set to Chennai + Tamil Nadu. This is one of the highest-impact local SEO levers available.
- **NAP consistency:** Name, Address, Phone must match exactly across the website footer, Google Business Profile, and any directory listings.
- **Location-aware landing content:** a short, genuinely useful "About/Shipping" section mentioning Chennai-based operations, delivery timelines across Tamil Nadu, and COD availability if offered — written naturally, not keyword-stuffed.
- **Local backlinks/citations (off-page, post-launch):** listings on Justdial, Sulekha, IndiaMART (if relevant), local fashion/lifestyle blogs, and Chennai business directories.
- **Tamil Nadu-relevant content marketing (optional, high-value):** blog/journal section (e.g. `/journal/`) with posts like "Best Streetwear Trends in Chennai 2026" or "Where to Wear Oversized Tees in Chennai's Weather" — targets long-tail local search intent and builds topical authority.
- **hreflang / language tag (optional):** if you plan a Tamil-language version later, add `hreflang="ta-IN"` alongside `en-IN`; not required for v1 if the site is English-only.

### 4.4 Sitemap, Robots & Indexing
- Auto-generate `sitemap.xml` via `django.contrib.sitemaps` — include Home, all Category pages, all Product pages, updated `lastmod` on stock/price changes.
- `robots.txt` — disallow `/cart/`, `/checkout/`, `/accounts/` (private/duplicate pages), allow all category/product pages.
- Submit sitemap to Google Search Console; verify domain there and monitor indexing/Core Web Vitals reports post-launch.
- Set up **Google Analytics 4** + **Google Search Console** from day one to track organic Chennai/Tamil Nadu traffic and search queries.

### 4.5 Django Implementation Notes
- Store SEO fields (`meta_title`, `meta_description`, `og_image`) directly on `Product` and `Category` models so admin can override defaults per item via Django Admin — auto-generate sensible defaults if left blank.
- Use a shared `base.html` block for `<title>`, `<meta name="description">`, Open Graph tags, and JSON-LD so every page template only needs to fill in the specifics.
- Cache category/product pages (Django's per-view or template-fragment caching) to keep load times fast — page speed is itself an SEO ranking factor.

---

## 5. SUGGESTED BUILD ORDER (MVP roadmap)

1. Django project setup + models (Product, Category, Variant, Cart, Order) + Django Admin config.
2. Auth (signup/login/logout) + Profile + Address.
3. Home + Category (PLP) + Product (PDP) pages with Tailwind styling.
4. Cart (session-based for guests, HTMX interactions).
5. Checkout flow + Cashfree sandbox integration + webhook handling.
6. Order history + order detail + invoice.
7. Polish: wishlist, search, coupons, reviews.
8. Move media to cloud storage, switch SQLite → PostgreSQL, deploy.

---

*This document is a starting blueprint — the dark theme color palette and category list are locked in per your input; typography and exact copy can still be refined once you have final brand assets (logo, product photography style).*
