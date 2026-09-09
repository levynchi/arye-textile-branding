from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


PACK_QTY = 3
VAT = Decimal("1.18")
WHITE_SLUG = "white"


def round_to_x9(raw: Decimal) -> Decimal:
    n = int(round((float(raw) - 9) / 10.0) * 10 + 9)
    return Decimal(max(9, n))


def fill_white_digital_prices(apps, schema_editor):
    WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
    WhiteProductVariant = apps.get_model("white_catalog", "WhiteProductVariant")
    products = WhiteSubcategory.objects.filter(category__slug=WHITE_SLUG)
    for product in products:
        variant_prices = []
        for variant in WhiteProductVariant.objects.filter(product=product, is_active=True):
            unit = variant.unit_price if variant.unit_price is not None else product.unit_price
            if unit is None:
                continue
            pack = (Decimal(unit) * PACK_QTY).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            raw = (pack * 2 * VAT).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            digital = round_to_x9(raw)
            variant.digital_price = digital
            variant.save(update_fields=["digital_price"])
            variant_prices.append(digital)
        if variant_prices:
            # Most common variant price as the product-level default.
            product.online_price = max(set(variant_prices), key=variant_prices.count)
            product.save(update_fields=["online_price"])
        elif product.unit_price is not None:
            pack = (Decimal(product.unit_price) * PACK_QTY).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            raw = (pack * 2 * VAT).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            product.online_price = round_to_x9(raw)
            product.save(update_fields=["online_price"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0027_user_hidden_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="whiteproductvariant",
            name="digital_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="מחיר מארז ללקוח הסופי כולל מע״מ. ריק = מחיר המוצר.",
                max_digits=10,
                null=True,
                verbose_name='מחיר לצרכן דיגיטלי (כולל מע"מ)',
            ),
        ),
        migrations.AlterField(
            model_name="whitesubcategory",
            name="online_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="מחיר מומלץ ללקוח הסופי במארז — כולל מע״מ. אם לגרסה יש מחיר משלה, הוא גובר בייצוא.",
                max_digits=10,
                null=True,
                verbose_name='מחיר לצרכן דיגיטלי (כולל מע"מ)',
            ),
        ),
        migrations.RunPython(fill_white_digital_prices, noop),
    ]
