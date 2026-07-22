import random
import os
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth.models import User
from store.models import Category, Product, ProductVariant, ProductImage

class Command(BaseCommand):
    help = 'Seeds initial categories, products, and variants for Twosomesty'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data seeding...")

        # 1. Ensure Superuser exists (for local testing convenience)
        superuser_username = 'admin'
        superuser_email = 'admin@twosomesty.com'
        superuser_pass = 'admin123'
        
        if not User.objects.filter(username=superuser_username).exists():
            User.objects.create_superuser(
                username=superuser_username,
                email=superuser_email,
                password=superuser_pass
            )
            self.stdout.write(self.style.SUCCESS(f"Created superuser: {superuser_username} with password: {superuser_pass}"))
        else:
            self.stdout.write("Superuser already exists.")

        # 2. Seed Categories
        categories_data = [
            {'name': 'T-Shirts', 'meta_title': 'Buy Trendy T-Shirts Online in Chennai | Twosomesty'},
            {'name': 'Jackets', 'meta_title': 'Premium Jackets Online in Chennai, Tamil Nadu | Twosomesty'},
            {'name': 'Jeans', 'meta_title': 'Best Fitting Jeans Online in Chennai | Twosomesty'},
            {'name': 'Hoodies', 'meta_title': 'Oversized Streetwear Hoodies in Chennai | Twosomesty'},
            {'name': 'Oversized Tees', 'meta_title': 'Buy Oversized Tees Online in Chennai, Tamil Nadu | Twosomesty'}
        ]

        categories_dir = os.path.join(settings.MEDIA_ROOT, 'categories')
        os.makedirs(categories_dir, exist_ok=True)
        
        cat_images_map = {
            'T-Shirts': 'IMG_5960.jpg',
            'Jackets': 'IMG_5763.png',
            'Jeans': 'IMG_5952.jpg',
            'Hoodies': 'IMG_5760.png',
            'Oversized Tees': 'IMG_5720.png'
        }

        categories = {}
        for cat_info in categories_data:
            name = cat_info['name']
            slug = slugify(name)
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'meta_title': cat_info['meta_title'],
                    'meta_description': f"Browse our collection of {name.lower()} with same-day dispatch in Chennai and shipping across Tamil Nadu."
                }
            )
            
            # Seed category image (run for both new and existing categories)
            img_fname = cat_images_map.get(name)
            if img_fname:
                src_path = os.path.join(settings.BASE_DIR, 'static', 'img', img_fname)
                if os.path.exists(src_path):
                    dest_filename = f"{slug}_{img_fname}"
                    dest_path = os.path.join(categories_dir, dest_filename)
                    if not os.path.exists(dest_path):
                        shutil.copy(src_path, dest_path)
                    cat.image = f"categories/{dest_filename}"
                    cat.save()
            
            categories[name] = cat
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {name}"))
            else:
                self.stdout.write(f"Category already exists: {name}")

        # 3. Seed Products, Variants
        # Sizes: S, M, L, XL
        # Colors: Jet Black, Off-White, Electric Blue, Sage Green
        colors = ['Jet Black', 'Off-White', 'Electric Blue', 'Sage Green']
        sizes = ['S', 'M', 'L', 'XL']

        products_data = [
            {
                'category': 'Oversized Tees',
                'name': 'Electric Velocity Oversized Tee',
                'description': 'Constructed from heavy 240 GSM organic cotton, the Electric Velocity Tee features a dropped shoulder fit, robust ribbed collar, and minimal brand embroidery. Tailored for comfort and style.',
                'base_price': 1499.00,
                'discount_price': 1199.00,
                'brand': 'Twosomesty'
            },
            {
                'category': 'Oversized Tees',
                'name': 'Midnight Nomad Graphic Tee',
                'description': 'A premium oversized graphic tee highlighting cyber-punk inspired screen prints on the back. Made from 100% pre-shrunk cotton.',
                'base_price': 1599.00,
                'discount_price': 1299.00,
                'brand': 'Twosomesty'
            },
            {
                'category': 'Hoodies',
                'name': 'Heavyweight Classic Hoodie',
                'description': 'Experience pure warmth with our 400 GSM double-fleece lined hoodie. Featuring a structured hood without drawcords for a clean, modern aesthetic, a kangaroo pocket, and elasticized cuffs.',
                'base_price': 2999.00,
                'discount_price': 2499.00,
                'brand': 'Twosomesty'
            },
            {
                'category': 'Jackets',
                'name': 'Urban Utility Bomber Jacket',
                'description': 'Water-resistant nylon shell utility jacket featuring quilted lining, inner zip pocket, and metal hardware. Ideal for layering during breezy seasons.',
                'base_price': 3999.00,
                'discount_price': 3499.00,
                'brand': 'Twosomesty'
            },
            {
                'category': 'Jeans',
                'name': 'Relaxed Fit Cargo Denim',
                'description': 'Loose, wide-leg utility cargo jeans built from durable 14oz denim. Equipped with side utility pockets, silver logo buttons, and standard belt loops.',
                'base_price': 2499.00,
                'discount_price': None,
                'brand': 'Twosomesty'
            },
            {
                'category': 'T-Shirts',
                'name': 'Essential Slub Cotton Tee',
                'description': 'Lightweight 180 GSM slub cotton tee perfect for hot weather. Breathable, durable, and featuring a soft-wash texture.',
                'base_price': 999.00,
                'discount_price': 799.00,
                'brand': 'Twosomesty'
            }
        ]

        media_products_dir = os.path.join(settings.MEDIA_ROOT, 'products')
        os.makedirs(media_products_dir, exist_ok=True)
        
        product_images_map = {
            'electric-velocity-oversized-tee': ['IMG_5720.png', 'IMG_5721.png'],
            'midnight-nomad-graphic-tee': ['IMG_5664.png', 'IMG_5666.png'],
            'heavyweight-classic-hoodie': ['IMG_5760.png', 'IMG_5761.png', 'IMG_5762.png'],
            'urban-utility-bomber-jacket': ['IMG_5763.png', 'IMG_5764.png', 'IMG_5766.png'],
            'relaxed-fit-cargo-denim': ['IMG_5952.jpg', 'IMG_5953.jpg', 'IMG_5954.jpg', 'IMG_5955.jpg'],
            'essential-slub-cotton-tee': ['IMG_5960.jpg', 'IMG_5961.jpg', 'IMG_5962.jpg', 'IMG_5963.jpg', 'IMG_5965.jpg', 'IMG_5966.jpg']
        }

        for prod_info in products_data:
            cat_name = prod_info['category']
            category = categories[cat_name]
            slug = slugify(prod_info['name'])
            
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': prod_info['name'],
                    'description': prod_info['description'],
                    'category': category,
                    'base_price': prod_info['base_price'],
                    'discount_price': prod_info['discount_price'],
                    'brand': prod_info['brand'],
                    'is_active': True
                }
            )

            # Copy images and seed ProductImage
            image_filenames = product_images_map.get(slug, [])
            for idx, fname in enumerate(image_filenames):
                src_path = os.path.join(settings.BASE_DIR, 'static', 'img', fname)
                if os.path.exists(src_path):
                    dest_filename = f"{slug}_{idx}_{fname}"
                    dest_path = os.path.join(media_products_dir, dest_filename)
                    if not os.path.exists(dest_path):
                        shutil.copy(src_path, dest_path)
                    ProductImage.objects.get_or_create(
                        product=product,
                        image=f"products/{dest_filename}",
                        defaults={'alt_text': f"{product.name} - View {idx + 1}"}
                    )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created product: {product.name}"))
                # Create variants for this product
                # Create a combination of sizes and colors to represent stock
                sku_counter = 1
                for color in colors:
                    for size in sizes:
                        sku = f"TWS-{product.id}-{sku_counter:03d}-{size}-{color.replace(' ', '').upper()}"
                        ProductVariant.objects.create(
                            product=product,
                            size=size,
                            color=color,
                            stock_qty=random.randint(10, 50),
                            sku=sku
                        )
                        sku_counter += 1
                self.stdout.write(f"  Created variants for {product.name}")
            else:
                self.stdout.write(f"Product already exists: {product.name}")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
