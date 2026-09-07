from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0026_price_percent_as_discount"),
    ]

    operations = [
        migrations.AddField(
            model_name="whitecataloguser",
            name="hidden_categories",
            field=models.ManyToManyField(
                blank=True,
                help_text="ברירת מחדל: הכל גלוי. סמן רק קטגוריות שהמשתמש לא יראה.",
                related_name="hidden_from_users",
                to="white_catalog.whitecategory",
                verbose_name="קטגוריות מוסתרות",
            ),
        ),
        migrations.AddField(
            model_name="whitecataloguser",
            name="hidden_products",
            field=models.ManyToManyField(
                blank=True,
                help_text="ברירת מחדל: הכל גלוי. סמן רק מוצרים שהמשתמש לא יראה.",
                related_name="hidden_from_users",
                to="white_catalog.whitesubcategory",
                verbose_name="מוצרים מוסתרים",
            ),
        ),
    ]
