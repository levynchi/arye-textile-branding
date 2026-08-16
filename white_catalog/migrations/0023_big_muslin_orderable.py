from decimal import Decimal

from django.db import migrations


PRODUCT_SLUG = "Big_muslin_baby_diapers"
COLOR_NAME = "חיות אוריגמי שחור"
BARCODE = "7297555001412"
PRICE = Decimal("31.90")


def forwards(apps, schema_editor):
    WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
    WhiteColor = apps.get_model("white_catalog", "WhiteColor")
    WhiteColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")

    product = WhiteSubcategory.objects.filter(slug=PRODUCT_SLUG).first()
    if product is None:
        return

    updates = []
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
        product.unit_price = PRICE
        updates.append("unit_price")
    if not (product.simple_price_label or "").strip():
        product.simple_price_label = "מארז"
        updates.append("simple_price_label")
    if updates:
        product.save(update_fields=updates)

    color, _ = WhiteColor.objects.get_or_create(name=COLOR_NAME)
    variant = WhiteColorVariant.objects.filter(barcode=BARCODE).first()
    if variant is None:
        variant = WhiteColorVariant.objects.filter(product=product, color=color).first()
    if variant is None:
        WhiteColorVariant.objects.create(
            product=product,
            color=color,
            barcode=BARCODE,
            unit_price=PRICE,
            is_active=True,
        )
        return
    variant.product = product
    variant.color = color
    variant.barcode = BARCODE
    variant.unit_price = PRICE
    variant.is_active = True
    variant.save()


def backwards(apps, schema_editor):
    WhiteColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")
    WhiteColorVariant.objects.filter(barcode=BARCODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0022_merge_printed_tetra_pages"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
