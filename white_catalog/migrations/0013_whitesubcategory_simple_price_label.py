from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0012_alter_whitesubcategory_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="whitesubcategory",
            name="simple_price_label",
            field=models.CharField(
                blank=True,
                default="יחידה",
                help_text="למשל: יחידה, מארז, סט",
                max_length=50,
                verbose_name="סוג מחיר למוצר פשוט",
            ),
        ),
    ]
