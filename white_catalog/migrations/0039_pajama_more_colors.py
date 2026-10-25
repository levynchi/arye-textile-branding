"""Add three more colors to the existing pajama set."""

from decimal import Decimal

from django.db import migrations


PAJAMA_SIZES = (("12-18", 3), ("18-24", 4), ("24-30", 5))
COLOR_NAMES = ("תכלת", "אפור בהיר", "ורוד בייבי עדין")
FALLBACK_PRICE = Decimal("22.30")


def attach_colors(apps, schema_editor):
	Subcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	SizeType = apps.get_model("white_catalog", "WhiteSizeType")
	Color = apps.get_model("white_catalog", "WhiteColor")
	ColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")
	Price = apps.get_model("white_catalog", "WhiteSubcategoryPrice")

	product = Subcategory.objects.filter(slug="pijama_set").first()
	if product is None:
		product = Subcategory.objects.filter(name="סט פיג'מה").first()
	if product is None:
		return

	price = product.unit_price if product.unit_price is not None else FALLBACK_PRICE
	sizes = []
	for name, order in PAJAMA_SIZES:
		size, _created = SizeType.objects.get_or_create(
			name=name,
			defaults={"order": order, "is_active": True},
		)
		sizes.append(size)
		if not Price.objects.filter(subcategory_id=product.pk, size_name=name).exists():
			Price.objects.create(
				subcategory_id=product.pk,
				size_name=name,
				price=price,
				order=size.order or order,
			)

	for color_name in COLOR_NAMES:
		color = Color.objects.filter(name=color_name).first()
		if color is None:
			continue
		for size in sizes:
			if ColorVariant.objects.filter(
				product_id=product.pk,
				color_id=color.pk,
				size_id=size.pk,
			).exists():
				continue
			ColorVariant.objects.create(
				product_id=product.pk,
				color_id=color.pk,
				size_id=size.pk,
				barcode=None,
				unit_price=price,
				is_active=True,
				order=size.order or 0,
			)
		for row in ColorVariant.objects.filter(
			product_id=product.pk,
			color_id=color.pk,
			size__isnull=True,
		):
			row.delete()


def backwards(apps, schema_editor):
	Subcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	Color = apps.get_model("white_catalog", "WhiteColor")
	ColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")

	product = Subcategory.objects.filter(slug="pijama_set").first()
	if product is None:
		product = Subcategory.objects.filter(name="סט פיג'מה").first()
	if product is None:
		return

	color_ids = list(
		Color.objects.filter(name__in=COLOR_NAMES).values_list("pk", flat=True)
	)
	ColorVariant.objects.filter(
		product_id=product.pk,
		color_id__in=color_ids,
		size__name__in=[name for name, _order in PAJAMA_SIZES],
	).delete()


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0038_flannel_kimono_set"),
	]

	operations = [
		migrations.RunPython(attach_colors, backwards),
	]
