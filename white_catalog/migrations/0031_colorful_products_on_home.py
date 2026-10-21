from django.db import migrations


def forwards(apps, schema_editor):
    WhiteCategory = apps.get_model("white_catalog", "WhiteCategory")
    WhiteCategory.objects.filter(slug="צבעוני").update(show_products_on_homepage=True)
    WhiteCategory.objects.filter(name="צבעוני").update(show_products_on_homepage=True)


def backwards(apps, schema_editor):
    WhiteCategory = apps.get_model("white_catalog", "WhiteCategory")
    WhiteCategory.objects.filter(slug="צבעוני").update(show_products_on_homepage=False)
    WhiteCategory.objects.filter(name="צבעוני").update(show_products_on_homepage=False)


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0030_colorful_pajama_set"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
