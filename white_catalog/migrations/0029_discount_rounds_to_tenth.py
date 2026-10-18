from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0028_variant_digital_price"),
    ]

    operations = [
        migrations.AlterField(
            model_name="whitecataloguser",
            name="price_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="0 = מחיר מלא. 10 = 10% הנחה (13 ₪ הופך ל־11.7). המחיר אחרי הנחה מעוגל לעשירית השקל.",
                max_digits=6,
                validators=[
                    MinValueValidator(Decimal("0.00")),
                    MaxValueValidator(Decimal("100.00")),
                ],
                verbose_name="אחוז הנחה ממחיר הקטלוג",
            ),
        ),
    ]
