from django.db import migrations


PAJAMA_SIZES = ("12-18", "18-24", "24-30")


def ensure_pajama_equal_sizes(apps, schema_editor):
	"""Give the pajama set the three sizes that are ordered as one quantity."""
	Subcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	SizeType = apps.get_model("white_catalog", "WhiteSizeType")
	ColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")
	Price = apps.get_model("white_catalog", "WhiteSubcategoryPrice")

	product = Subcategory.objects.filter(slug="pigama").first()
	if product is None:
		return

	sizes = []
	for index, name in enumerate(PAJAMA_SIZES, start=1):
		size, _created = SizeType.objects.get_or_create(
			name=name,
			defaults={"order": index, "is_active": True},
		)
		sizes.append(size)
		if product.unit_price is not None and not Price.objects.filter(subcategory_id=product.pk, size_name=name).exists():
			Price.objects.create(
				subcategory_id=product.pk,
				size_name=name,
				price=product.unit_price,
				order=size.order or index,
			)

	unsized = list(ColorVariant.objects.filter(product_id=product.pk, size__isnull=True))
	for variant in unsized:
		if ColorVariant.objects.filter(
			product_id=product.pk,
			color_id=variant.color_id,
			size__isnull=False,
		).exists():
			if variant.barcode:
				variant.barcode = None
				variant.save(update_fields=["barcode"])
			variant.delete()
			continue
		barcode = (variant.barcode or "").strip() or None
		if barcode:
			variant.barcode = None
			variant.save(update_fields=["barcode"])
		image_name = variant.image.name if variant.image else ""
		unit_price = variant.unit_price if variant.unit_price is not None else product.unit_price
		for index, size in enumerate(sizes):
			created = ColorVariant(
				product_id=product.pk,
				color_id=variant.color_id,
				size_id=size.pk,
				barcode=barcode if index == 0 else None,
				unit_price=unit_price,
				is_active=variant.is_active,
				order=size.order or index,
			)
			if image_name:
				created.image = image_name
			created.save()
		variant.delete()


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0033_pajama_size_copy"),
	]

	operations = [
		migrations.RunPython(ensure_pajama_equal_sizes, migrations.RunPython.noop),
	]
