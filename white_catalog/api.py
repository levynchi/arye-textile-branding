"""JSON API for importing product variants from the desktop app (optitex_analyzer).

Authentication: shared secret token in the X-API-Token header, configured via the
WHITE_CATALOG_API_TOKEN environment variable (see arye_site/settings).
"""

import base64
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import (
	WhiteColor,
	WhiteColorVariant,
	WhiteFabricType,
	WhiteProductVariant,
	WhiteSizeType,
	WhiteSubcategory,
)


def _token_valid(request):
	expected = (getattr(settings, 'WHITE_CATALOG_API_TOKEN', '') or '').strip()
	if not expected:
		# No token configured — API is disabled.
		return False
	provided = (request.headers.get('X-API-Token') or '').strip()
	return provided == expected


def _forbidden():
	return JsonResponse({'error': 'invalid or missing X-API-Token'}, status=403)


@require_GET
def export_meta(request):
	"""Return products, fabric types and size types so the desktop app can present choices."""
	if not _token_valid(request):
		return _forbidden()
	products = [
		{
			'id': p.id,
			'name': p.name,
			'category': p.category.name if p.category_id else '',
			'has_order_variants': p.has_order_variants,
			'has_color_variants': p.has_color_variants,
		}
		for p in WhiteSubcategory.objects.select_related('category').order_by('order', 'name')
	]
	fabric_types = list(
		WhiteFabricType.objects.filter(is_active=True).order_by('order', 'name').values_list('name', flat=True)
	)
	size_types = list(
		WhiteSizeType.objects.filter(is_active=True).order_by('order', 'name').values_list('name', flat=True)
	)
	return JsonResponse({
		'products': products,
		'fabric_types': fabric_types,
		'size_types': size_types,
	})


def _parse_price(value):
	raw = str(value or '').strip().replace(',', '')
	if not raw:
		return None
	try:
		return Decimal(raw)
	except InvalidOperation:
		raise ValueError(f'מחיר לא תקין: {value}')


def _import_color_row(product, row, color_name, price, barcode):
	"""Create/update a WhiteColorVariant for a color-fan row.

	Returns True when a new variant was created, False when updated.
	Raises ValueError with a Hebrew message for row-level errors.
	"""
	color_hex = str(row.get('color_hex') or '').strip()
	color, _ = WhiteColor.objects.get_or_create(name=color_name)
	if color_hex and color.hex_color != color_hex.lower():
		color.hex_color = color_hex
		color.save()

	variant = None
	if barcode:
		variant = WhiteColorVariant.objects.filter(barcode=barcode).first()
		if variant is not None and variant.product_id != product.id:
			raise ValueError(
				f'הברקוד {barcode} כבר משויך לצבע של מוצר אחר ({variant.product.name})'
			)
	if variant is None:
		variant = WhiteColorVariant.objects.filter(product=product, color=color).first()

	was_created = variant is None
	if variant is None:
		variant = WhiteColorVariant(product=product, color=color)
	else:
		variant.color = color
	if barcode:
		variant.barcode = barcode
	if price is not None:
		variant.unit_price = price

	image_b64 = row.get('image_base64') or ''
	if image_b64:
		try:
			data = base64.b64decode(image_b64)
		except Exception:
			raise ValueError('תמונת הצבע אינה base64 תקין')
		ext = str(row.get('image_format') or 'jpg').strip().lower() or 'jpg'
		safe_name = (barcode or color.name or 'color').replace(' ', '_')
		variant.image.save(f'{safe_name}.{ext}', ContentFile(data), save=False)
		# אותה תמונה משמשת גם כדוגמית הצבע במניפה (טקסטורת הבד במקום צבע אחיד)
		color.swatch_image.save(f'swatch_{safe_name}.{ext}', ContentFile(data), save=True)

	variant.save()

	# ברקוד שנתפס בעבר בטעות על וריאנט מידה של אותו מוצר - משוחרר לטובת הצבע
	if barcode:
		stale = WhiteProductVariant.objects.filter(product=product, barcode=barcode).first()
		if stale is not None:
			stale.barcode = None
			stale.save(update_fields=['barcode'])

	return was_created


@csrf_exempt
@require_POST
def import_variants(request):
	"""Create/update WhiteProductVariant rows for an existing product.

	Expected JSON body::

		{
			"product_id": 3,
			"fabric_type": "פלנל",              # default fabric for all rows
			"rows": [
				{"size": "0-3", "barcode": "729...", "unit_price": "12.5", "fabric_type": ""},
				...
			]
		}

	Rows are matched by barcode first (idempotent re-runs), then by the
	(product, fabric, size) unique combination.

	Rows that carry a "color" key are treated as color-fan rows instead: they
	create/update WhiteColorVariant (with optional "color_hex", and an optional
	"image_base64"/"image_format" pair for the fabric swatch image), and no size
	is required for them.
	"""
	if not _token_valid(request):
		return _forbidden()

	try:
		payload = json.loads(request.body.decode('utf-8'))
	except (ValueError, UnicodeDecodeError):
		return JsonResponse({'error': 'invalid JSON body'}, status=400)

	product_id = payload.get('product_id')
	default_fabric = str(payload.get('fabric_type') or '').strip()
	rows = payload.get('rows') or []
	if not product_id:
		return JsonResponse({'error': 'product_id is required'}, status=400)
	if not isinstance(rows, list) or not rows:
		return JsonResponse({'error': 'rows must be a non-empty list'}, status=400)

	try:
		product = WhiteSubcategory.objects.get(pk=product_id)
	except WhiteSubcategory.DoesNotExist:
		return JsonResponse({'error': f'product {product_id} not found'}, status=404)

	created = 0
	updated = 0
	deleted = 0
	color_rows_seen = False
	errors = []
	warnings = []

	for i, row in enumerate(rows, start=1):
		size_name = str(row.get('size') or '').strip()
		barcode = str(row.get('barcode') or '').strip()
		fabric_name = str(row.get('fabric_type') or '').strip() or default_fabric
		color_name = str(row.get('color') or '').strip()

		# מחיקת צבע למוצר לפי ברקוד (או לפי שם צבע אם אין ברקוד)
		if row.get('delete') or str(row.get('action') or '').strip().lower() == 'delete':
			try:
				with transaction.atomic():
					qs = WhiteColorVariant.objects.filter(product=product)
					if barcode:
						qs = qs.filter(barcode=barcode)
					elif color_name:
						qs = qs.filter(color__name=color_name)
					else:
						errors.append(f'שורה {i}: למחיקה נדרש ברקוד או שם צבע')
						continue
					count, _ = qs.delete()
					if count:
						deleted += count
					else:
						warnings.append(f'שורה {i}: לא נמצא צבע למחיקה')
			except Exception as exc:
				errors.append(f'שורה {i}: {exc}')
			continue

		if color_name:
			# שורת צבע ממניפת הצבעים - נקלטת כ"צבע למוצר", ללא צורך במידה
			color_rows_seen = True
			try:
				price = _parse_price(row.get('unit_price'))
			except ValueError as exc:
				errors.append(f'שורה {i}: {exc}')
				continue
			try:
				with transaction.atomic():
					if _import_color_row(product, row, color_name, price, barcode):
						created += 1
					else:
						updated += 1
			except ValueError as exc:
				errors.append(f'שורה {i}: {exc}')
			except Exception as exc:
				errors.append(f'שורה {i}: {exc}')
			continue

		if not size_name:
			errors.append(f'שורה {i}: חסרה מידה')
			continue
		if not fabric_name:
			errors.append(f'שורה {i}: חסר סוג בד')
			continue
		try:
			price = _parse_price(row.get('unit_price'))
		except ValueError as exc:
			errors.append(f'שורה {i}: {exc}')
			continue

		try:
			with transaction.atomic():
				fabric, _ = WhiteFabricType.objects.get_or_create(name=fabric_name)
				size, _ = WhiteSizeType.objects.get_or_create(name=size_name)

				existing_by_barcode = None
				if barcode:
					existing_by_barcode = WhiteProductVariant.objects.filter(barcode=barcode).first()

				if existing_by_barcode is not None:
					if existing_by_barcode.product_id != product.id:
						errors.append(
							f'שורה {i}: הברקוד {barcode} כבר משויך למוצר אחר '
							f'({existing_by_barcode.product.name})'
						)
						continue
					existing_by_barcode.fabric_type = fabric
					existing_by_barcode.size_type = size
					if price is not None:
						existing_by_barcode.unit_price = price
					existing_by_barcode.save()
					updated += 1
					continue

				variant, was_created = WhiteProductVariant.objects.get_or_create(
					product=product,
					fabric_type=fabric,
					size_type=size,
					defaults={'barcode': barcode or None, 'unit_price': price},
				)
				if was_created:
					created += 1
				else:
					if barcode:
						variant.barcode = barcode
					if price is not None:
						variant.unit_price = price
					variant.save()
					updated += 1
		except Exception as exc:
			errors.append(f'שורה {i}: {exc}')

	# Make the imported variants actually visible on the site.
	if color_rows_seen and (created or updated):
		# מצב צבעים ומצב "גרסאות + מארזים" לא חיים יחד - ייבוא צבעים קובע מצב צבעים
		flag_updates = []
		if not product.has_color_variants:
			product.has_color_variants = True
			flag_updates.append('has_color_variants')
			warnings.append('המוצר סומן אוטומטית כ"הזמנה לפי מניפת צבעים"')
		if product.has_order_variants:
			product.has_order_variants = False
			flag_updates.append('has_order_variants')
			warnings.append('מצב "גרסאות + מארזים" כובה כדי שמניפת הצבעים תוצג')
		if flag_updates:
			product.save(update_fields=flag_updates)
	if (created or updated) and not color_rows_seen and not product.has_order_variants:
		if product.has_color_variants:
			warnings.append(
				'המוצר מוגדר להזמנה לפי מניפת צבעים — הגרסאות נשמרו אך לא יוצגו '
				'עד שינוי מצב המוצר באדמין'
			)
		else:
			product.has_order_variants = True
			product.save(update_fields=['has_order_variants'])
			warnings.append('המוצר סומן אוטומטית כ"יש לו גרסאות + מארזים"')

	return JsonResponse({
		'product': product.name,
		'created': created,
		'updated': updated,
		'deleted': deleted,
		'errors': errors,
		'warnings': warnings,
	})
