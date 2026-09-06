from decimal import Decimal

from django.db import migrations, models


def copy_percent_from_price_list(apps, schema_editor):
    WhiteCatalogUser = apps.get_model("white_catalog", "WhiteCatalogUser")
    for user in WhiteCatalogUser.objects.select_related("price_list").all():
        percent = Decimal("100.00")
        if user.price_list_id and user.price_list.percent_of_list is not None:
            percent = user.price_list.percent_of_list
        if user.price_percent != percent:
            user.price_percent = percent
            user.save(update_fields=["price_percent"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0024_whitepricelist"),
    ]

    operations = [
        migrations.AddField(
            model_name="whitecataloguser",
            name="price_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("100.00"),
                help_text="100 = מחיר הקטלוג המלא. 96.15 ≈ 12.50 כשהרשימה 13. 92.31 ≈ 12.00.",
                max_digits=6,
                verbose_name="אחוז ממחיר הקטלוג",
            ),
        ),
        migrations.RunPython(copy_percent_from_price_list, noop_reverse),
        migrations.RemoveField(
            model_name="whitecataloguser",
            name="price_list",
        ),
        migrations.DeleteModel(
            name="WhitePriceList",
        ),
    ]
