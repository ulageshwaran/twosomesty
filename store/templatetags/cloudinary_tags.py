"""
cloudinary_tags.py — Image URL helpers (storage-backend agnostic).

After migrating from Cloudinary to Cloudflare R2, on-the-fly URL transforms
are no longer available. The filters below return the raw URL from whatever
storage backend is active.

For R2:
  - `cloudinary_optimize` → returns image.url as-is (no transform injected)
  - `cloudinary_srcset`   → returns a srcset with the same URL at all widths
                            (browser will still download the same file; add
                             Cloudflare Image Resizing later for true srcset)

Template usage is unchanged — no template edits needed.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _get_url(image_or_url):
    """Extract a raw URL string from either an ImageField or a plain string."""
    if not image_or_url:
        return ''
    if hasattr(image_or_url, 'url'):
        return image_or_url.url
    return str(image_or_url)


# ---------------------------------------------------------------------------
# Filter: {{ image_field|cloudinary_optimize:"w_300" }}
# Returns the raw storage URL (Cloudflare R2 or local) unchanged.
# The filter argument is accepted but ignored for non-Cloudinary backends.
# ---------------------------------------------------------------------------
@register.filter(name='cloudinary_optimize')
def cloudinary_optimize(image_or_url, args=""):
    """
    Returns the image URL from the active storage backend.

    Previously injected Cloudinary URL transformation parameters (width,
    quality, format). Now returns the URL unchanged for any backend.

    Usage (unchanged from before):
        {{ product.images.first.image|cloudinary_optimize:"w_300" }}
    """
    return _get_url(image_or_url)


# ---------------------------------------------------------------------------
# Simple tag: {% cloudinary_url image_field width=300 %}
# Returns a plain URL string (same URL regardless of width arg).
# ---------------------------------------------------------------------------
@register.simple_tag
def cloudinary_url(image_field, width=None, height=None, crop="limit",
                   quality="auto", fetch_format="auto"):
    """
    Returns the storage URL for the given image field.
    Width/height/quality args are accepted for template compatibility but ignored.
    """
    return _get_url(image_field)


# ---------------------------------------------------------------------------
# Simple tag: {% cloudinary_srcset image_field widths="300,600,900" %}
# Returns a srcset string. Without Cloudflare Image Resizing all descriptors
# point to the same URL — the browser still benefits from the sizes= hint
# for layout. Enable Cloudflare Image Resizing later for true multi-size srcset.
# ---------------------------------------------------------------------------
@register.simple_tag
def cloudinary_srcset(image_field, widths="300,600,900", quality="auto",
                      fetch_format="auto", crop="limit"):
    """
    Generates a srcset attribute value.
    All widths currently resolve to the same R2 URL.

    Usage:
        srcset="{% cloudinary_srcset product.images.first.image widths='300,600,900' %}"
    """
    url = _get_url(image_field)
    if not url:
        return ''
    parts = [f"{url} {w.strip()}w" for w in widths.split(',') if w.strip()]
    return mark_safe(', '.join(parts))
