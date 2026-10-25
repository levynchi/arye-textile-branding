"""Show the pajama set with the new navy, zebra, and leopard photos.

The product already exists. The zebra full set becomes the main image.
Navy and leopard are added to the gallery. Each of those colors uses its
photo on sizes 12-18, 18-24, and 24-30. Price, fabric text, and colors stay
as they are.
"""

from pathlib import Path

from django.core.files import File
from django.db import migrations


PRODUCT_SLUG = "pijama_set"
PRODUCT_NAME = "סט פיג'מה"
SIZE_NAMES = ("12-18", "18-24", "24-30")
ASSETS = Path(__file__).resolve().parent.parent / "product_assets"
ZEBRA_FILE = ASSETS / "pajama_zebra.jpg"
ZEBRA_NAME = "pajama_zebra.jpg"
GALLERY = (
	(ASSETS / "pajama_navy.jpg", "pajama_navy.jpg", "כחול ניבי", 1),
	(ASSETS / "pajama_leopard.jpg", "pajama_leopard.jpg", "מנומר חום", 2),
)
COLOR_PHOTOS = (
	("כחול ניבי", ASSETS / "pajama_navy.jpg", "pajama_navy.jpg"),
	("זברה", ZEBRA_FILE, ZEBRA_NAME),
	("מנומר חום", ASSETS / "pajama_leopard.jpg", "pajama_leopard.jpg"),
)


def _basename(field):
	return Path(getattr(field, "name", "") or "").name


def _is_target_file(field, stored_name):
	base = _basename(field)
	if not base:
		return False
	stem = Path(stored_name).stem
	suffix = Path(stored_name).suffix.lower()
	if not base.lower().endswith(suffix):
		return False
	return base == stored_name or base.startswith(stem + "_")


def _upload(instance, field_name, path, stored_name):
	field = getattr(instance, field_name)
	if _is_target_file(field, stored_name):
		return field.name
	if field:
		field.delete(save=False)
	if not path.is_file():
		raise FileNotFoundError(path)
	with path.open("rb") as handle:
		getattr(instance, field_name).save(stored_name, File(handle), save=True)
	return getattr(instance, field_name).name


def _assign_shared_photo(rows, path, stored_name):
	if not rows:
		return
	names = {row.image.name for row in rows if row.image}
	if len(names) == 1 and all(_is_target_file(row.image, stored_name) for row in rows):
		return
	shared = _upload(rows[0], "image", path, stored_name)
	for row in rows[1:]:
		if row.image.name == shared:
			continue
		if row.image:
			row.image.delete(save=False)
		row.image = shared
		row.save(update_fields=["image"])


def _add_gallery(image_model, product, path, stored_name, alt_text, order):
	existing = image_model.objects.filter(subcategory_id=product.pk)
	if existing.filter(alt_text=alt_text).exists():
		return
	if existing.filter(image__endswith=stored_name).exists():
		return
	gallery = image_model(subcategory=product, alt_text=alt_text, order=order)
	_upload(gallery, "image", path, stored_name)


def forwards(apps, schema_editor):
	Subcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	Gallery = apps.get_model("white_catalog", "WhiteSubcategoryImage")
	SizeType = apps.get_model("white_catalog", "WhiteSizeType")
	Color = apps.get_model("white_catalog", "WhiteColor")
	ColorVariant = apps.get_model("white_catalog", "WhiteColorVariant")

	product = Subcategory.objects.filter(slug=PRODUCT_SLUG).first()
	if product is None:
		product = Subcategory.objects.filter(name=PRODUCT_NAME).first()
	if product is None:
		return

	_upload(product, "image", ZEBRA_FILE, ZEBRA_NAME)
	for path, stored_name, alt_text, order in GALLERY:
		_add_gallery(Gallery, product, path, stored_name, alt_text, order)

	size_ids = list(SizeType.objects.filter(name__in=SIZE_NAMES).values_list("pk", flat=True))
	if not size_ids:
		return

	for color_name, path, stored_name in COLOR_PHOTOS:
		color = Color.objects.filter(name=color_name).first()
		if color is None:
			continue
		rows = list(
			ColorVariant.objects.filter(
				product_id=product.pk,
				color_id=color.pk,
				size_id__in=size_ids,
			).order_by("id")
		)
		_assign_shared_photo(rows, path, stored_name)


def backwards(apps, schema_editor):
	# Leave the product and its photos in place.
	pass


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0039_pajama_more_colors"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
