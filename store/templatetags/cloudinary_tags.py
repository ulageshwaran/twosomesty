from django import template

register = template.Library()

@register.filter(name='cloudinary_optimize')
def cloudinary_optimize(image_or_url, args="w_1400,q_90"):
    """
    Transforms Cloudinary image URLs to high-resolution ~1MB image quality (w_1400, q_90).
    Usage in Django templates:
      {{ product.images.first.image|cloudinary_optimize:"w_1400,q_90" }}
    """
    if not image_or_url:
        return ''

    if hasattr(image_or_url, 'url'):
        url = image_or_url.url
    else:
        url = str(image_or_url)

    if 'res.cloudinary.com' in url and '/upload/' in url:
        transformations = ["f_auto"]
        if args:
            transformations.extend(args.split(','))
        else:
            transformations.extend(["w_1400", "q_90"])
        transform_str = ','.join(transformations)
        return url.replace('/upload/', f'/upload/{transform_str}/')

    return url


@register.simple_tag
def cloudinary_url(image_field, width=1400, height=None, crop="limit", quality="90", fetch_format="auto"):
    """
    Generates high-resolution (~1MB) Cloudinary URLs.
    """
    if not image_field:
        return ''
    
    url = getattr(image_field, 'url', str(image_field))
    
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
