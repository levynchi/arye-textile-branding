"""Add a colorful flannel double-zip romper in sizes 0-3 and 3-6.

Four sample photos become the product images and the photos of the
matching colors. Pink and the galaxy print stay on the color fan only.
"""

from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.db import migrations
from django.utils.text import slugify


CATEGORY_NAME = "צבעוני"
CATEGORY_SLUG = "צבעוני"
PRODUCT_NAME = "אוברול ריץ רץ כפול צבעוני"
PRODUCT_SLUG = "colorful_double_zip_romper"
ROMPER_SIZES = (("0-3", 0), ("3-6", 1))
PRICE = Decimal("26.00")
ASSETS = Path(__file__).resolve().parent.parent / "product_assets"
SEA_GIRLS = ASSETS / "romper_sea_girls.jpg"
BUTTERFLIES = ASSETS / "romper_butterflies.jpg"
SEA_BOYS = ASSETS / "romper_sea_boys.jpg"
GRAY = ASSETS / "romper_gray.jpg"
COLOR_NAMES = (
	"אלמוגי ים בנים",
	"אפור בהיר",
	"ורוד",
	"ממלכת הים בנות",
	"פרפרים",
	"שחור חלליות וגלקסיות",
)
COLOR_PHOTOS = {
	"ממלכת הים בנות": (SEA_GIRLS, "romper_sea_girls.jpg"),
	"פרפרים": (BUTTERFLIES, "romper_butterflies.jpg"),
	"אלמוגי ים בנים": (SEA_BOYS, "romper_sea_boys.jpg"),
	"אפור בהיר": (GRAY, "romper_gray.jpg"),
}
GALLERY = (
	("פרפרים", BUTTERFLIES, "romper_butterflies.jpg", 1),
	("אלמוגי ים בנים", SEA_BOYS, "romper_sea_boys.jpg", 2),
	("אפור בהיר", GRAY, "romper_gray.jpg", 3),
)
DESCRIPTION = "אוברול ריץ רץ כפול צבעוני מפלנל. נמכר רק בפלנל, במידות 0-3 ו-3-6."
INFORMATION = "<p>אוברול ארוך עם ריץ רץ כפול. פלנל, 100% כותנה.</p>"
FABRIC = "<p>פלנל בלבד.</p>"
SIZES = "<p>מידות 0-3 ו-3-6. בהזמנה מזינים כמות אחת, והיא נלקחת משתי המידות.</p>"


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
			simple_price_label="יחידה",
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
		if updates:
			product.save(update_fields=updates)

	_save_image(product, "image", SEA_GIRLS, "romper_sea_girls.jpg")
	for alt_text, path, stored_name, order in GALLERY:
		if WhiteSubcategoryImage.objects.filter(subcategory=product, alt_text=alt_text).exists():
			continue
		gallery = WhiteSubcategoryImage(subcategory=product, alt_text=alt_text, order=order)
		_save_image(gallery, "image", path, stored_name)

	price = product.unit_price if product.unit_price is not None else PRICE
	sizes = []
	for name, order in ROMPER_SIZES:
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
		photo = COLOR_PHOTOS.get(color_name)
		for size in sizes:
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
			if photo:
				_save_image(variant, "image", photo[0], photo[1])
		for row in ColorVariant.objects.filter(
			product_id=product.pk,
			color_id=color.pk,
			size__isnull=True,
		):
			row.delete()


def backwards(apps, schema_editor):
	WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	WhiteSubcategory.objects.filter(slug=PRODUCT_SLUG).delete()
	WhiteSubcategory.objects.filter(name=PRODUCT_NAME).delete()


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0040_pajama_color_photos"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
