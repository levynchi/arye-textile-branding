from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


PRODUCT_NAME = "מארז חיתולי טטרה מודפס 3"
CATEGORY_NAME = "חיתולי בד / טטרה"
PRODUCT_SLUG = "מארז-חיתולי-טטרה-מודפס-3"
CATEGORY_SLUG = "חיתולי-בד-טטרה"


def forwards(apps, schema_editor):
    WhiteCategory = apps.get_model("white_catalog", "WhiteCategory")
    WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")

    category, created = WhiteCategory.objects.get_or_create(
        name=CATEGORY_NAME,
        defaults={"order": 50, "slug": CATEGORY_SLUG},
    )
    if not created and not (category.slug or "").strip():
        category.slug = category.slug or slugify(CATEGORY_NAME, allow_unicode=True) or CATEGORY_SLUG
        category.save(update_fields=["slug"])

    product = WhiteSubcategory.objects.filter(name=PRODUCT_NAME).first()
    if product is None:
        WhiteSubcategory.objects.create(
            category=category,
            name=PRODUCT_NAME,
            slug=PRODUCT_SLUG,
            is_orderable=True,
            has_color_variants=True,
            has_order_variants=False,
            unit_price=Decimal("22.50"),
            simple_price_label="מארז",
            sizes="80x80",
        )
        return

    updates = []
    if product.category_id is None:
        product.category = category
        updates.append("category")
    if not product.is_orderable:
        product.is_orderable = True
        updates.append("is_orderable")
    if not product.has_color_variants:
        product.has_color_variants = True
        updates.append("has_color_variants")
    if product.has_order_variants:
        product.has_order_variants = False
        updates.append("has_order_variants")
    if product.unit_price is None:
        product.unit_price = Decimal("22.50")
        updates.append("unit_price")
    if not (product.simple_price_label or "").strip():
        product.simple_price_label = "מארז"
        updates.append("simple_price_label")
    if not (product.sizes or "").strip():
        product.sizes = "80x80"
        updates.append("sizes")
    if not (product.slug or "").strip():
        product.slug = PRODUCT_SLUG
        updates.append("slug")
    if updates:
        product.save(update_fields=updates)


def backwards(apps, schema_editor):
    WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
    WhiteSubcategory.objects.filter(name=PRODUCT_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0020_clothing_threes_only"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
