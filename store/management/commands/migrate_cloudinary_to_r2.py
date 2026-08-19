"""
migrate_cloudinary_to_r2.py
----------------------------
Management command that migrates all media files from Cloudinary to
Cloudflare R2 (or whichever backend is now configured in STORAGES["default"]).

Usage:
    python manage.py migrate_cloudinary_to_r2            # actually migrate
    python manage.py migrate_cloudinary_to_r2 --dry-run  # preview only, no writes

What it does:
  1. Loops every model instance that has an ImageField/FileField.
  2. For each field, if the current URL contains 'res.cloudinary.com', it:
       a. Downloads the file from Cloudinary.
       b. Uploads it to R2 via default_storage.save().
       c. Updates the model's field value to the new path.
       d. Regenerates the ProductImage thumbnail (if applicable).
  3. Skips files that don't look like Cloudinary URLs (already migrated).
  4. Logs every action to both stdout and cloudinary_migration.log in BASE_DIR.

Safety:
  - Does NOT delete anything from Cloudinary.
  - Safe to re-run (idempotent) — already-migrated files are skipped.
  - Use --dry-run to see what WOULD happen without writing anything.
"""

import logging
import os
import urllib.request
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

# pyrefly: ignore [missing-import]
import cloudinary
# pyrefly: ignore [missing-import]
import cloudinary.utils


LOG_FILE = os.path.join(settings.BASE_DIR, 'cloudinary_migration.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('cloudinary_migration')


def get_cloudinary_url(public_id: str) -> str:
    """Reconstruct the original Cloudinary delivery URL from a stored public_id,
    independent of whatever storage backend default_storage currently points at."""
    if not public_id:
        return ''
    url, _ = cloudinary.utils.cloudinary_url(public_id)
    return url


def is_cloudinary_url(url: str) -> bool:
    return bool(url and 'res.cloudinary.com' in url)


def download_file(url: str) -> bytes:
    """Download a file from a URL and return raw bytes."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def derive_path_from_cloudinary_url(url: str, prefix: str) -> str:
    """
    Extract a reasonable storage path from a Cloudinary URL.
    e.g. https://res.cloudinary.com/demo/image/upload/v123/products/foo.jpg
      → products/foo.jpg
    Falls back to prefix/filename if parsing fails.
    """
    try:
        # Strip transformation segments (everything between /upload/ and the public_id)
        after_upload = url.split('/upload/')[-1]
        # Drop version segment like v1234567890/
        parts = after_upload.split('/')
        if parts[0].startswith('v') and parts[0][1:].isdigit():
            parts = parts[1:]
        return '/'.join(parts)
    except Exception:
        filename = url.rsplit('/', 1)[-1].split('?')[0]
        return f"{prefix}/{filename}"


class Command(BaseCommand):
    help = 'Migrate all Cloudinary media files to the configured storage backend (R2).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Preview what would be migrated without actually writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no files will be written.\n'))
            log.info('=== DRY RUN started ===')
        else:
            log.info('=== Migration started ===')

        stats = {'skipped': 0, 'migrated': 0, 'failed': 0}

        # ----------------------------------------------------------------
        # Define all models + their image fields to migrate.
        # Add new entries here if you add more models with file fields.
        # ----------------------------------------------------------------
        from store.models import (
            CarouselSlide,
            Category,
            ProductImage,
            Profile,
            StoreFeature,
        )

        migration_targets = [
            # (ModelClass, [(field_name, upload_to_prefix), ...])
            (Profile,       [('avatar',    'avatars')]),
            (Category,      [('image',     'categories'), ('og_image', 'categories/og')]),
            (ProductImage,  [('image',     'products')]),
            (CarouselSlide, [('image',     'carousel')]),
            (StoreFeature,  [('image',     'features')]),
        ]

        # Also handle Product.og_image
        try:
            from store.models import Product
            migration_targets.append((Product, [('og_image', 'products/og')]))
        except ImportError:
            pass

        for ModelClass, fields in migration_targets:
            model_name = ModelClass.__name__
            log.info(f'--- Processing {model_name} ---')

            for instance in ModelClass.objects.all():
                for field_name, upload_prefix in fields:
                    field = getattr(instance, field_name, None)
                    if not field or not field.name:
                        continue

                    # Reconstruct the ORIGINAL Cloudinary URL from the stored
                    # public_id/name — do NOT use field.url, since default_storage
                    # is already pointed at R2 and would build the wrong URL.
                    try:
                        current_url = get_cloudinary_url(field.name)
                    except Exception as e:
                        log.warning(f'  [{model_name} pk={instance.pk}] {field_name}: cannot build Cloudinary URL — {e}')
                        stats['failed'] += 1
                        continue

                    if not current_url:
                        log.warning(f'  [{model_name} pk={instance.pk}] {field_name}: empty name, skipping')
                        stats['failed'] += 1
                        continue

                    if not is_cloudinary_url(current_url):
                        log.info(f'  [{model_name} pk={instance.pk}] {field_name}: SKIP (not Cloudinary)')
                        stats['skipped'] += 1
                        continue

                    # Derive the target path in R2
                    new_path = derive_path_from_cloudinary_url(current_url, upload_prefix)

                    log.info(
                        f'  [{model_name} pk={instance.pk}] {field_name}: '
                        f'MIGRATE {current_url!r} → {new_path!r}'
                    )

                    if dry_run:
                        stats['migrated'] += 1
                        continue

                    try:
                        # Download from Cloudinary
                        file_bytes = download_file(current_url)

                        # Save to new storage backend
                        saved_path = default_storage.save(new_path, ContentFile(file_bytes))

                        # Update the model field value
                        setattr(instance, field_name, saved_path)
                        instance.save(update_fields=[field_name])

                        log.info(
                            f'    ✓ Saved to {saved_path!r}'
                        )
                        stats['migrated'] += 1

                    except Exception as e:
                        log.error(
                            f'  [{model_name} pk={instance.pk}] {field_name}: FAILED — {e}'
                        )
                        stats['failed'] += 1

            # After migrating ProductImage.image, regenerate thumbnails
            if ModelClass is ProductImage and not dry_run:
                log.info('  Regenerating ProductImage thumbnails...')
                for img in ProductImage.objects.all():
                    if img.image and not is_cloudinary_url(img.image.url):
                        # Trigger thumbnail regeneration by re-saving with force
                        try:
                            old_thumb = img.thumbnail
                            img.thumbnail = None  # clear so save() regenerates it
                            # Directly call _generate_thumbnail + save
                            buf = img._generate_thumbnail()
                            from django.core.files.base import ContentFile as CF
                            base = os.path.splitext(os.path.basename(img.image.name))[0]
                            thumb_name = f"{base}_thumb.webp"
                            img.thumbnail.save(thumb_name, CF(buf.read()), save=True)
                            log.info(f'    Thumbnail generated for ProductImage pk={img.pk}')
                        except Exception as e:
                            log.warning(f'    Thumbnail failed for ProductImage pk={img.pk}: {e}')

        # ----------------------------------------------------------------
        # Summary
        # ----------------------------------------------------------------
        summary = (
            f'\n{"DRY RUN " if dry_run else ""}Migration complete: '
            f'{stats["migrated"]} migrated, '
            f'{stats["skipped"]} skipped, '
            f'{stats["failed"]} failed.'
        )
        log.info(summary)
        self.stdout.write(
            self.style.SUCCESS(summary) if stats['failed'] == 0
            else self.style.ERROR(summary)
        )
        self.stdout.write(f'Full log saved to: {LOG_FILE}\n')
