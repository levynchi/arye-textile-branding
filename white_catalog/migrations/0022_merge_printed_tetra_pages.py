from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import migrations


KEEP_SLUG = "muslin_baby_diapers"
DUPLICATE_NAME = "מארז חיתולי טטרה מודפס 3"


def _copy_file_to_gallery(WhiteSubcategoryImage, dest, src_field, alt, order, existing_names):
    if not src_field or not getattr(src_field, "name", ""):
        return existing_names
    basename = src_field.name.rsplit("/", 1)[-1]
    if basename in existing_names:
        return existing_names
    try:
        src_field.open("rb")
        data = src_field.read()
        src_field.close()
    except Exception:
        return existing_names
    row = WhiteSubcategoryImage(subcategory=dest, alt_text=alt or "", order=order)
    row.image.save(basename, ContentFile(data), save=True)
    existing_names.add(basename)
    return existing_names


def forwards(apps, schema_editor):
    WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
    WhiteSubcategoryImage = apps.get_model("white_catalog", "WhiteSubcategoryImage")
    WhiteColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")
    WhiteCartItem = apps.get_model("white_catalog", "WhiteCartItem")
    WhiteOrderItem = apps.get_model("white_catalog", "WhiteOrderItem")

    keep = WhiteSubcategory.objects.filter(slug=KEEP_SLUG).first()
    duplicate = WhiteSubcategory.objects.filter(name=DUPLICATE_NAME).exclude(slug=KEEP_SLUG).first()
    if keep is None or duplicate is None:
        return

    updates = []
    if not keep.is_orderable:
        keep.is_orderable = True
        updates.append("is_orderable")
    if not keep.has_color_variants:
        keep.has_color_variants = True
        updates.append("has_color_variants")
    if keep.has_order_variants:
        keep.has_order_variants = False
        updates.append("has_order_variants")
    if keep.unit_price is None:
        keep.unit_price = Decimal("22.50")
        updates.append("unit_price")
    if updates:
        keep.save(update_fields=updates)

    keep_color_ids = set(
        WhiteColorVariant.objects.filter(product=keep).values_list("color_id", flat=True)
    )
    for variant in WhiteColorVariant.objects.filter(product=duplicate):
        if variant.color_id in keep_color_ids:
            continue
        variant.product = keep
        variant.save(update_fields=["product"])
        keep_color_ids.add(variant.color_id)

    WhiteCartItem.objects.filter(product=duplicate).update(product=keep)
    WhiteOrderItem.objects.filter(product=duplicate).update(product=keep)

    existing_names = set()
    if keep.image:
        existing_names.add(keep.image.name.rsplit("/", 1)[-1])
    for img in keep.images.all():
        if img.image:
            existing_names.add(img.image.name.rsplit("/", 1)[-1])

    next_order = (keep.images.order_by("-order").values_list("order", flat=True).first() or 0) + 1
    existing_names = _copy_file_to_gallery(
        WhiteSubcategoryImage, keep, duplicate.image, duplicate.name, next_order, existing_names
    )
    next_order += 1
    for img in duplicate.images.all().order_by("order", "id"):
        existing_names = _copy_file_to_gallery(
            WhiteSubcategoryImage,
            keep,
            img.image,
            img.alt_text or duplicate.name,
            next_order,
            existing_names,
        )
        next_order += 1

    duplicate.delete()


def backwards(apps, schema_editor):
    # The duplicate page is not recreated; variants stay on muslin_baby_diapers.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("white_catalog", "0021_printed_tetra_pack"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
