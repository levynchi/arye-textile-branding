from django.db import migrations, models


def forwards(apps, schema_editor):
    WhiteCatalogUser = apps.get_model("white_catalog", "WhiteCatalogUser")
    WhitePackType = apps.get_model("white_catalog", "WhitePackType")
    WhiteCatalogUser.objects.exclude(pack_route="threes").update(pack_route="threes")
    WhitePackType.objects.filter(quantity=5).update(is_active=False)


def backwards(apps, schema_editor):
    WhitePackType = apps.get_model("white_catalog", "WhitePackType")
    WhitePackType.objects.filter(quantity=5).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0019_whitecolor_whiteorderitem_barcode_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="whitecataloguser",
            name="pack_route",
            field=models.CharField(
                choices=[
                    ("both", "גם שלישיות וגם חמישיות"),
                    ("threes", "שלישיות בלבד"),
                    ("fives", "חמישיות בלבד"),
                ],
                default="threes",
                help_text="ביגוד מוזמן בשלישיות בלבד. חמישיות לא בשימוש.",
                max_length=10,
                verbose_name="מסלול מוצרים",
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
