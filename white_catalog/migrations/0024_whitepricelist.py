from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


CATALOG_LISTS = (
    {
        "name": "קטלוג / חנות",
        "slug": "catalog",
        "percent_of_list": Decimal("100.00"),
        "is_default": True,
        "order": 0,
    },
    {
        "name": "סיטונאי בינוני",
        "slug": "medium",
        "percent_of_list": Decimal("96.15"),
        "is_default": False,
        "order": 1,
    },
    {
        "name": "סיטונאי גדול",
        "slug": "large",
        "percent_of_list": Decimal("92.31"),
        "is_default": False,
        "order": 2,
    },
)


def seed_price_lists(apps, schema_editor):
    WhitePriceList = apps.get_model("white_catalog", "WhitePriceList")
    WhiteCatalogUser = apps.get_model("white_catalog", "WhiteCatalogUser")
    for data in CATALOG_LISTS:
        WhitePriceList.objects.update_or_create(slug=data["slug"], defaults=data)
    catalog = WhitePriceList.objects.get(slug="catalog")
    WhiteCatalogUser.objects.filter(price_list__isnull=True).update(price_list=catalog)


def unseed_price_lists(apps, schema_editor):
    WhiteCatalogUser = apps.get_model("white_catalog", "WhiteCatalogUser")
    WhitePriceList = apps.get_model("white_catalog", "WhitePriceList")
    WhiteCatalogUser.objects.update(price_list=None)
    WhitePriceList.objects.filter(slug__in=("catalog", "medium", "large")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0023_big_muslin_orderable"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhitePriceList",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="שם מחירון")),
                ("slug", models.SlugField(max_length=50, unique=True, verbose_name="Slug")),
                (
                    "percent_of_list",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="100 = מחיר הקטלוג המלא. 92.31 = סיטונאי גדול (12 ₪ כשהרשימה 13).",
                        max_digits=6,
                        verbose_name="אחוז ממחיר הקטלוג",
                    ),
                ),
                ("is_default", models.BooleanField(default=False, verbose_name="ברירת מחדל")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="סדר תצוגה")),
            ],
            options={
                "verbose_name": "מחירון",
                "verbose_name_plural": "מחירונים",
                "ordering": ("order", "name"),
            },
        ),
        migrations.AddField(
            model_name="whitecataloguser",
            name="price_list",
            field=models.ForeignKey(
                blank=True,
                help_text="המחירון שלפיו הלקוח רואה ומזמין מחירים באתר.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="customers",
                to="white_catalog.whitepricelist",
                verbose_name="מחירון",
            ),
        ),
        migrations.RunPython(seed_price_lists, unseed_price_lists),
    ]
