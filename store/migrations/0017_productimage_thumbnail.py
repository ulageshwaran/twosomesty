# Generated manually during Cloudinary → R2 migration
# Adds thumbnail ImageField to ProductImage for Pillow-generated 300px WebP thumbnails.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_alter_category_options_category_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='thumbnail',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='products/thumbs/',
                help_text='Auto-generated 300px WebP thumbnail (do not upload manually).',
            ),
        ),
    ]
