from django.db import migrations


OLD_PLAIN = "בהזמנה אין בחירת מידה — בוחרים צבע ומזינים כמות סטים."
OLD_ENTITY = "בהזמנה אין בחירת מידה &mdash; בוחרים צבע ומזינים כמות סטים."
NEW = "בהזמנה מזינים כמות אחת, והיא נלקחת מכל מידה. 2 אומר שני סטים מכל מידה."


def update_size_copy(apps, schema_editor):
	Subcategory = apps.get_model("white_catalog", "WhiteSubcategory")
	for product in Subcategory.objects.filter(sizes__contains="בהזמנה אין בחירת מידה"):
		product.sizes = product.sizes.replace(OLD_PLAIN, NEW).replace(OLD_ENTITY, NEW)
		product.save(update_fields=["sizes"])


class Migration(migrations.Migration):

	dependencies = [
		("white_catalog", "0032_color_variant_size"),
	]

	operations = [
		migrations.RunPython(update_size_copy, migrations.RunPython.noop),
	]
