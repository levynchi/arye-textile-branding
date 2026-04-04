from django.db import migrations, models


def copy_orderable_to_variant_flag(apps, schema_editor):
    WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
    WhiteSubcategory.objects.filter(is_orderable=True).update(has_order_variants=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0010_variant_unit_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="whitesubcategory",
            name="has_order_variants",
            field=models.BooleanField(
                default=False,
                help_text="סמן אם המוצר מוזמן דרך גרסאות, מידות וסוגי מארזים",
                verbose_name="יש לו גרסאות + מארזים",
            ),
        ),
        migrations.AlterField(
            model_name="whitesubcategory",
            name="is_orderable",
            field=models.BooleanField(
                default=False,
                help_text="האם מוצר זה זמין להזמנה בקטלוג הלבן",
                verbose_name="זמין להזמנה",
            ),
        ),
        migrations.AlterField(
            model_name="whitecartitem",
            name="pack_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="cart_items",
                to="white_catalog.whitepacktype",
                verbose_name="סוג מארז",
            ),
        ),
        migrations.AlterField(
            model_name="whitecartitem",
            name="quantity",
            field=models.PositiveIntegerField(default=1, verbose_name="כמות"),
        ),
        migrations.AlterField(
            model_name="whitecartitem",
            name="variant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="cart_items",
                to="white_catalog.whiteproductvariant",
                verbose_name="גרסה",
            ),
        ),
        migrations.RunPython(copy_orderable_to_variant_flag, noop_reverse),
    ]
