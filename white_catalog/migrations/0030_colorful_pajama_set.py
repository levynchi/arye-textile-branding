"""Add the colorful category and the flannel pajama set.

Ordering uses the existing color fan: one barcode per color, quantity of sets.
Size stays in the product text. No fabric picker and no pack sizes.
"""

from pathlib import Path

from django.core.files import File
from django.db import migrations
from django.utils.text import slugify


CATEGORY_NAME = "צבעוני"
CATEGORY_SLUG = "צבעוני"
PRODUCT_NAME = "סט פיג'מה"
PRODUCT_SLUG = "סט-פיגמה"
ASSETS = Path(__file__).resolve().parent.parent / "product_assets"
SHIRT_FILE = ASSETS / "pajama_shirt.jpg"
PANTS_FILE = ASSETS / "pajama_pants.jpg"
PANTS_ALT = "מכנסי הפיג'מה"

DESCRIPTION = "סט פיג'מה מפלנל: חולצה ארוכה ומכנסיים. נמכר רק בפלנל."
INFORMATION = "<p>הסט כולל חולצה עם שרוול ארוך ומכנסיים תואמים. על התווית: 100% כותנה.</p>"
FABRIC = "<p>פלנל בלבד.</p>"
SIZES = (
	"<p>המידה מודפסת על התווית (למשל 18-24). "
	"בהזמנה אין בחירת מידה — בוחרים צבע ומזינים כמות סטים.</p>"
)


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

	category = WhiteCategory.objects.filter(name=CATEGORY_NAME).first()
	if category is None:
		category = WhiteCategory.objects.filter(slug=CATEGORY_SLUG).first()
	if category is None:
		category = WhiteCategory.objects.create(
			name=CATEGORY_NAME,
			slug=CATEGORY_SLUG,
			order=100,
		)
	elif not (category.slug or "").strip():
		category.slug = slugify(CATEGORY_NAME, allow_unicode=True) or CATEGORY_SLUG
		category.save(update_fields=["slug"])

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
			is_orderable=True,
			has_color_variants=True,
			has_order_variants=False,
			simple_price_label="סט",
		)
	else:
		updates = []
		if product.category_id is None:
			product.category = category
			updates.append("category")
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
		if not (product.description or "").strip():
			product.description = DESCRIPTION
			updates.append("description")
		if not (product.information or "").strip():
			product.information = INFORMATION
			updates.append("information")
		if not (product.fabric_production or "").strip():
			product.fabric_production = FABRIC
			updates.append("fabric_production")
		if not (product.sizes or "").strip():
			product.sizes = SIZES
			updates.append("sizes")
		if not (product.slug or "").strip():
			product.slug = PRODUCT_SLUG
			updates.append("slug")
		if updates:
			product.save(update_fields=updates)

	_save_image(product, "image", SHIRT_FILE, "pajama_set_shirt.jpg")

	if not WhiteSubcategoryImage.objects.filter(subcategory=product, alt_text=PANTS_ALT).exists():
		gallery = WhiteSubcategoryImage(
			subcategory=product,
			alt_text=PANTS_ALT,
			order=1,
		)
		_save_image(gallery, "image", PANTS_FILE, "pajama_set_pants.jpg")


def backwards(apps, schema_editor):
	WhiteCategory = apps.get_model("white_catalog", "WhiteCategory")
	WhiteSubcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	WhiteSubcategory.objects.filter(slug=PRODUCT_SLUG).delete()
	WhiteSubcategory.objects.filter(name=PRODUCT_NAME).delete()
	category = WhiteCategory.objects.filter(name=CATEGORY_NAME).first()
	if category is not None and not category.subcategories.exists():
		category.delete()


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0029_discount_rounds_to_tenth"),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
