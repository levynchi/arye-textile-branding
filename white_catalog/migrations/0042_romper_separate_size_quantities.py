"""Order the colorful romper by size, and price it per romper.

Pajama sets keep one quantity copied onto every size. This romper does not:
0-3 and 3-6 are ordered on their own. The price suffix comes from
simple_price_label, so this product reads לאוברול and the pajama stays לסט.
"""

from django.db import migrations, models


PRODUCT_SLUG = "colorful_double_zip_romper"
PRODUCT_NAME = "אוברול ריץ רץ כפול צבעוני"
OLD_NOTE = "בהזמנה מזינים כמות אחת, והיא נלקחת משתי המידות."
NEW_NOTE = "כל מידה מוזמנת בנפרד."


def separate_romper_sizes(apps, schema_editor):
	Product = apps.get_model("white_catalog", "WhiteSubcategory")
	product = Product.objects.filter(slug=PRODUCT_SLUG).first()
	if product is None:
		product = Product.objects.filter(name=PRODUCT_NAME).first()
	if product is None:
		return
	product.simple_price_label = "אוברול"
	product.sizes_share_quantity = False
	updates = ["simple_price_label", "sizes_share_quantity"]
	sizes = product.sizes or ""
	if OLD_NOTE in sizes:
		product.sizes = sizes.replace(OLD_NOTE, NEW_NOTE)
		updates.append("sizes")
	product.save(update_fields=updates)


def restore_shared_romper_sizes(apps, schema_editor):
	Product = apps.get_model("white_catalog", "WhiteSubcategory")
	product = Product.objects.filter(slug=PRODUCT_SLUG).first()
	if product is None:
		product = Product.objects.filter(name=PRODUCT_NAME).first()
	if product is None:
		return
	product.simple_price_label = "יחידה"
	product.sizes_share_quantity = True
	updates = ["simple_price_label", "sizes_share_quantity"]
	sizes = product.sizes or ""
	if NEW_NOTE in sizes:
		product.sizes = sizes.replace(NEW_NOTE, OLD_NOTE)
		updates.append("sizes")
	product.save(update_fields=updates)


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0041_colorful_double_zip_romper"),
	]

	operations = [
		migrations.AddField(
			model_name="whitesubcategory",
			name="sizes_share_quantity",
			field=models.BooleanField(
				default=True,
				help_text="כשצבע כולל כמה מידות, כמות אחת מועתקת לכל מידה. בטל כדי להזמין כל מידה בנפרד",
				verbose_name="כמות אחת לכל המידות",
			),
		),
		migrations.RunPython(separate_romper_sizes, restore_shared_romper_sizes),
	]
