from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import F


def invert_price_percent(apps, schema_editor):
    WhiteCatalogUser = apps.get_model("white_catalog", "WhiteCatalogUser")
    WhiteCatalogUser.objects.update(price_percent=Decimal("100.00") - F("price_percent"))


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0025_user_price_percent"),
    ]

    operations = [
        migrations.RunPython(invert_price_percent, invert_price_percent),
        migrations.AlterField(
            model_name="whitecataloguser",
            name="price_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="0 = מחיר מלא. 10 = 10% הנחה (13 ₪ הופך ל־11.70).",
                max_digits=6,
                validators=[
                    MinValueValidator(Decimal("0.00")),
                    MaxValueValidator(Decimal("100.00")),
                ],
                verbose_name="אחוז הנחה ממחיר הקטלוג",
            ),
        ),
    ]
