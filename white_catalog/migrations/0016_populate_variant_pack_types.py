from django.db import migrations


def populate_variant_pack_types(apps, schema_editor):
    """Assign all active pack types to existing variants so behavior is unchanged."""
    WhiteProductVariant = apps.get_model("white_catalog", "WhiteProductVariant")
    WhitePackType = apps.get_model("white_catalog", "WhitePackType")

    active_pack_type_ids = list(
        WhitePackType.objects.filter(is_active=True).values_list("id", flat=True)
    )
    if not active_pack_type_ids:
        return

    for variant in WhiteProductVariant.objects.all():
        variant.pack_types.set(active_pack_type_ids)


def reverse_populate(apps, schema_editor):
    WhiteProductVariant = apps.get_model("white_catalog", "WhiteProductVariant")
    for variant in WhiteProductVariant.objects.all():
        variant.pack_types.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0015_whitecataloguser_pack_route_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_variant_pack_types, reverse_populate),
    ]
