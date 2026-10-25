"""Add a flannel wrap-bodysuit and footed-legging set in size 0-3.

Colors come from the existing fan. The two sample photos are the product
images, and each is also the photo for its matching color.
"""

from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.db import migrations
from django.utils.text import slugify


CATEGORY_NAME = "צבעוני"
CATEGORY_SLUG = "צבעוני"
PRODUCT_NAME = "בגד גוף מעטפת + רגלית"
PRODUCT_SLUG = "kimono_bodysuit_leggings"
SIZE_NAME = "0-3"
PRICE = Decimal("25.00")
ASSETS = Path(__file__).resolve().parent.parent / "product_assets"
GALAXY_FILE = ASSETS / "kimono_set_galaxy.jpg"
PINK_FILE = ASSETS / "kimono_set_pink.jpg"
COLOR_NAMES = ("כחול ניבי", "מנומר חום", "ורוד בייבי", "שחור חלליות וגלקסיות")
COLOR_PHOTOS = {
	"שחור חלליות וגלקסיות": (GALAXY_FILE, "kimono_set_galaxy.jpg"),
	"ורוד בייבי": (PINK_FILE, "kimono_set_pink.jpg"),
}
DESCRIPTION = "בגד גוף מעטפת ורגלית מפלנל. נמכר רק בפלנל, רק במידה 0-3."
INFORMATION = "<p>הסט כולל בגד גוף מעטפת ורגלית תואמת. פלנל, 100% כותנה.</p>"
FABRIC = "<p>פלנל בלבד.</p>"
SIZES = "<p>מידה 0-3 בלבד.</p>"


def _save_image(instance, field_name, path, stored_name):
	field = getattr(instance, field_name)
	if field:
		return
	if not path.is_file():
		raise FileNotFoundError(path)
	with path.open("rb") as handle:
		field.save(stored_name, File(handle), save=True)


def forwards(apps, schema_editor):
	WhiteCategory = apps.get_model("white_catalog", "WhiteCategory")
	WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	WhiteSubcategoryImage = apps.get_model("white_catalog", "WhiteSubcategoryImage")
	SizeType = apps.get_model("white_catalog", "WhiteSizeType")
	Color = apps.get_model("white_catalog", "WhiteColor")
	ColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")
	Price = apps.get_model("white_catalog", "WhiteSubcategoryPrice")

	category = WhiteCategory.objects.filter(name=CATEGORY_NAME).first()
	if category is None:
		category = WhiteCategory.objects.filter(slug=CATEGORY_SLUG).first()
	if category is None:
		category = WhiteCategory.objects.create(
			name=CATEGORY_NAME,
			slug=slugify(CATEGORY_NAME, allow_unicode=True) or CATEGORY_SLUG,
			order=100,
		)

	product = (
		WhiteSubcategory.objects.filter(slug=PRODUCT_SLUG).first()
		or WhiteSubcategory.objects.filter(name=PRODUCT_NAME).first()
	)
	if product is None:
		product = WhiteSubcategory.objects.create(
			category=category,
			name=PRODUCT_NAME,
			slug=PRODUCT_SLUG,
			description=DESCRIPTION,
			information=INFORMATION,
			fabric_production=FABRIC,
			sizes=SIZES,
			unit_price=PRICE,
			is_orderable=True,
			has_color_variants=True,
			has_order_variants=False,
			simple_price_label="סט",
		)
	else:
		updates = []
		for field, value in (
			("description", DESCRIPTION),
			("information", INFORMATION),
			("fabric_production", FABRIC),
			("sizes", SIZES),
		):
			if getattr(product, field) != value:
				setattr(product, field, value)
				updates.append(field)
		if product.unit_price is None:
			product.unit_price = PRICE
			updates.append("unit_price")
		if not product.is_orderable:
			product.is_orderable = True
			updates.append("is_orderable")
		if not product.has_color_variants:
			product.has_color_variants = True
			updates.append("has_color_variants")
		if product.has_order_variants:
			product.has_order_variants = False
			updates.append("has_order_variants")
		if not (product.simple_price_label or "").strip() or product.simple_price_label == "יחידה":
			product.simple_price_label = "סט"
			updates.append("simple_price_label")
		if updates:
			product.save(update_fields=updates)

	_save_image(product, "image", GALAXY_FILE, "kimono_set_galaxy.jpg")
	if not WhiteSubcategoryImage.objects.filter(subcategory=product, alt_text="ורוד בייבי").exists():
		gallery = WhiteSubcategoryImage(subcategory=product, alt_text="ורוד בייבי", order=1)
		_save_image(gallery, "image", PINK_FILE, "kimono_set_pink.jpg")

	size, _created = SizeType.objects.get_or_create(
		name=SIZE_NAME,
		defaults={"order": 0, "is_active": True},
	)
	price = product.unit_price if product.unit_price is not None else PRICE
	if not Price.objects.filter(subcategory_id=product.pk, size_name=SIZE_NAME).exists():
		Price.objects.create(
			subcategory_id=product.pk,
			size_name=SIZE_NAME,
			price=price,
			order=size.order or 0,
		)

	for color_name in COLOR_NAMES:
		color = Color.objects.filter(name=color_name).first()
		if color is None:
			continue
		variant = ColorVariant.objects.filter(
			product_id=product.pk,
			color_id=color.pk,
			size_id=size.pk,
		).first()
		if variant is None:
			variant = ColorVariant.objects.create(
				product_id=product.pk,
				color_id=color.pk,
				size_id=size.pk,
				barcode=None,
				unit_price=price,
				is_active=True,
				order=size.order or 0,
			)
		photo = COLOR_PHOTOS.get(color_name)
		if photo:
			_save_image(variant, "image", photo[0], photo[1])


def backwards(apps, schema_editor):
	WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	WhiteSubcategory.objects.filter(slug=PRODUCT_SLUG).delete()
	WhiteSubcategory.objects.filter(name=PRODUCT_NAME).delete()


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0037_cotton_pajama_set"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
