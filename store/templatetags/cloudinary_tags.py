from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _build_cloudinary_url(url, width=None, height=None, crop="limit", quality="auto", fetch_format="auto", extra=None):
    """
    Core helper: inject Cloudinary transformation params into a /upload/ URL.
    Always uses q_auto and f_auto unless overridden.
    """
    if not url or 'res.cloudinary.com' not in url or '/upload/' not in url:
        return url or ''

    params = [f"f_{fetch_format}", f"q_{quality}"]
    if width:
        params.append(f"w_{width}")
    if height:
        params.append(f"h_{height}")
    if crop:
        params.append(f"c_{crop}")
    if extra:
        params.extend(extra if isinstance(extra, list) else [extra])

    return url.replace('/upload/', f'/upload/{",".join(params)}/')


def _get_url(image_or_url):
    """Extract a raw URL string from either a field or a plain string."""
    if not image_or_url:
        return ''
    if hasattr(image_or_url, 'url'):
        return image_or_url.url
    return str(image_or_url)


# ---------------------------------------------------------------------------
# Filter: {{ image_field|cloudinary_optimize:"w_300" }}
# Accepts comma-separated Cloudinary params as the filter arg.
# Always injects f_auto,q_auto first; caller can override q by passing q_xx.
# ---------------------------------------------------------------------------
@register.filter(name='cloudinary_optimize')
def cloudinary_optimize(image_or_url, args=""):
    """
    Transforms Cloudinary image URLs with automatic quality & format selection.
    Defaults: f_auto, q_auto.  Additional params are appended.

    Usage:
        {{ product.images.first.image|cloudinary_optimize:"w_300" }}
        {{ product.images.first.image|cloudinary_optimize:"w_800,c_fill" }}
    """
    url = _get_url(image_or_url)
    if not url or 'res.cloudinary.com' not in url or '/upload/' not in url:
        return url

    # Always start with f_auto,q_auto; caller args are appended after
    base_params = ["f_auto", "q_auto"]
    if args:
        base_params.extend(args.split(','))

    transform_str = ','.join(base_params)
    return url.replace('/upload/', f'/upload/{transform_str}/')


# ---------------------------------------------------------------------------
# Simple tag: {% cloudinary_url image_field width=300 %}
# Returns a plain URL string.
# ---------------------------------------------------------------------------
@register.simple_tag
def cloudinary_url(image_field, width=None, height=None, crop="limit", quality="auto", fetch_format="auto"):
    """
    Generates an optimised Cloudinary URL string (q_auto, f_auto by default).

    Usage:
        {% cloudinary_url product.images.first.image width=300 %}
    """
    url = _get_url(image_field)
    return _build_cloudinary_url(url, width=width, height=height, crop=crop,
                                  quality=quality, fetch_format=fetch_format)


# ---------------------------------------------------------------------------
# Simple tag: {% cloudinary_srcset image_field widths="300,600,900" %}
# Returns a ready-to-use srcset attribute value string.
# ---------------------------------------------------------------------------
@register.simple_tag
def cloudinary_srcset(image_field, widths="300,600,900", quality="auto", fetch_format="auto", crop="limit"):
    """
    Generates a srcset attribute value for responsive images.

    Usage:
        srcset="{% cloudinary_srcset product.images.first.image widths='300,600,900' %}"
    """
    url = _get_url(image_field)
    if not url or 'res.cloudinary.com' not in url or '/upload/' not in url:
        return url

    parts = []
    for w in widths.split(','):
        w = w.strip()
        if w:
            transformed = _build_cloudinary_url(url, width=int(w), crop=crop,
                                                  quality=quality, fetch_format=fetch_format)
            parts.append(f"{transformed} {w}w")
    return mark_safe(', '.join(parts))
