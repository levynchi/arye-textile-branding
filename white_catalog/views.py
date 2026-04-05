import json
import logging
from functools import wraps
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (
    WhiteCategory, WhiteSubcategory, WhiteCatalogUser, WhiteCatalogUserActivity,
    WhiteFabricType, WhiteProductVariant, WhiteVariantPackPrice, WhitePackType,
    WhiteCart, WhiteCartItem, WhiteOrder, WhiteOrderItem,
)
from .middleware import get_client_ip


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _catalog_session_login(request, user):
    """Persist the white catalog session for the selected user."""
    request.session["white_catalog_user_id"] = user.id
    request.session["white_catalog_username"] = user.username
    request.session["white_catalog_company_name"] = user.company_name


def _sync_admin_to_catalog_user(django_user, raw_password=None):
    """Map a Django staff/superuser account into a WhiteCatalogUser account."""
    if not getattr(django_user, "is_authenticated", False):
        return None
    if not django_user.is_active or not (django_user.is_staff or django_user.is_superuser):
        return None

    full_name = (
        django_user.get_full_name().strip()
        or getattr(django_user, "first_name", "").strip()
        or django_user.get_username()
    )
    defaults = {
        "company_name": "Admin Test Account",
        "contact_name": full_name,
        "contact_phone": "",
        "is_active": True,
    }
    catalog_user, created = WhiteCatalogUser.objects.get_or_create(
        username=django_user.get_username(),
        defaults=defaults,
    )

    update_fields = []
    if not catalog_user.company_name:
        catalog_user.company_name = defaults["company_name"]
        update_fields.append("company_name")
    if not catalog_user.contact_name:
        catalog_user.contact_name = full_name
        update_fields.append("contact_name")
    if catalog_user.contact_phone is None:
        catalog_user.contact_phone = ""
        update_fields.append("contact_phone")
    if not catalog_user.is_active:
        catalog_user.is_active = True
        update_fields.append("is_active")
    if raw_password:
        catalog_user.set_password(raw_password)
        update_fields.append("password_hash")

    if created or update_fields:
        catalog_user.save(update_fields=update_fields or None)

    return catalog_user


def get_current_catalog_user(request):
    """Return the logged-in WhiteCatalogUser or None."""
    user_id = request.session.get("white_catalog_user_id")
    if not user_id:
        admin_catalog_user = _sync_admin_to_catalog_user(getattr(request, "user", None))
        if admin_catalog_user:
            _catalog_session_login(request, admin_catalog_user)
            return admin_catalog_user
        return None
    try:
        return WhiteCatalogUser.objects.get(pk=user_id, is_active=True)
    except WhiteCatalogUser.DoesNotExist:
        admin_catalog_user = _sync_admin_to_catalog_user(getattr(request, "user", None))
        if admin_catalog_user:
            _catalog_session_login(request, admin_catalog_user)
            return admin_catalog_user
        return None


def require_catalog_login(view_func):
    """Decorator: redirect unauthenticated users to login page."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not get_current_catalog_user(request):
            return redirect(f"/white-catalog/login/?next={request.path}")
        return view_func(request, *args, **kwargs)
    return wrapper


def get_or_create_active_cart(user):
    """Return the user's active cart, creating one if needed."""
    cart, _ = WhiteCart.objects.get_or_create(user=user, status=WhiteCart.STATUS_ACTIVE)
    return cart


def _build_cart_page_context(request):
    """Cart, grouped line items, and count for cart page / drawer."""
    user = get_current_catalog_user(request)
    if not user:
        return {"cart": None, "grouped_items": [], "cart_count": 0}
    try:
        cart = WhiteCart.objects.prefetch_related(
            "items__product__images", "items__variant__fabric_type", "items__variant__size_type", "items__pack_type"
        ).get(user=user, status=WhiteCart.STATUS_ACTIVE)
    except WhiteCart.DoesNotExist:
        cart = None

    grouped_items = []
    if cart:
        groups_map = {}
        for item in cart.items.all():
            if not item.variant_id or not item.pack_type_id:
                key = ("simple", item.product_id)
            else:
                key = (item.product_id, item.variant.fabric_type_id, item.pack_type_id)
            if key not in groups_map:
                group = {
                    "product": item.product,
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "product_image": item.product.get_main_image(),
                    "fabric_type": item.display_fabric_name,
                    "pack_type": item.display_pack_name,
                    "price_at_add": item.price_at_add,
                    "items": [],
                    "group_total": Decimal("0"),
                    "items_by_variant_id": {},
                    "is_simple": item.is_simple_item,
                }
                if item.variant_id and item.pack_type_id:
                    group["pack_type_obj"] = item.pack_type
                    group["fabric_type_id"] = item.variant.fabric_type_id
                groups_map[key] = group
                grouped_items.append(group)
            groups_map[key]["items_by_variant_id"][item.variant_id or f"simple-{item.product_id}"] = item
            groups_map[key]["group_total"] += item.price_at_add * item.quantity

        for group in grouped_items:
            if group["is_simple"]:
                existing_item = group["items_by_variant_id"].get(f"simple-{group['product'].id}")
                group["items"].append(
                    {
                        "item_id": existing_item.id if existing_item else "",
                        "variant_id": "",
                        "pack_type_id": "",
                        "size_name": "יחידות",
                        "quantity": existing_item.quantity if existing_item else 0,
                        "line_total": "{:.2f}".format(existing_item.get_line_total() if existing_item else Decimal('0')),
                        "has_item": bool(existing_item),
                        "is_simple": True,
                    }
                )
            else:
                variants = (
                    group["product"].variants.filter(
                        is_active=True,
                        fabric_type_id=group["fabric_type_id"],
                    )
                    .select_related("size_type")
                    .order_by("size_type_id", "id")
                )
                for variant in variants:
                    existing_item = group["items_by_variant_id"].get(variant.id)
                    quantity = existing_item.quantity if existing_item else 0
                    line_total = existing_item.get_line_total() if existing_item else Decimal("0")
                    group["items"].append(
                        {
                            "item_id": existing_item.id if existing_item else "",
                            "variant_id": variant.id,
                            "pack_type_id": group["pack_type_obj"].id,
                            "size_name": variant.size_type.name,
                            "quantity": quantity,
                            "line_total": "{:.2f}".format(line_total),
                            "has_item": bool(existing_item),
                            "is_simple": False,
                        }
                    )
            del group["items_by_variant_id"]
            del group["product"]
            if "pack_type_obj" in group:
                del group["pack_type_obj"]
            if "fabric_type_id" in group:
                del group["fabric_type_id"]

    return {
        "cart": cart,
        "grouped_items": grouped_items,
        "cart_count": cart.get_item_count() if cart else 0,
    }


def _build_order_grouped_items(order):
    """Group submitted order items like the cart drawer summary."""
    grouped_items = []
    groups_map = {}

    for item in order.items.all():
        is_simple = not item.variant_id
        if is_simple:
            key = ("simple", item.product_id or item.product_name)
        else:
            fabric_name = item.variant.fabric_type.name if item.variant_id and item.variant and item.variant.fabric_type_id else item.variant_name
            key = (item.product_id or item.product_name, fabric_name, item.pack_type_name)

        if key not in groups_map:
            product_image = item.product.get_main_image() if item.product_id and item.product else None
            group = {
                "product_name": item.product_name,
                "product_image": product_image,
                "fabric_type": (
                    "ללא גרסאות"
                    if is_simple
                    else (item.variant.fabric_type.name if item.variant_id and item.variant and item.variant.fabric_type_id else item.variant_name)
                ),
                "pack_type": item.pack_type_name,
                "price_at_add": item.unit_price,
                "items": [],
                "group_total": Decimal("0"),
                "is_simple": is_simple,
            }
            groups_map[key] = group
            grouped_items.append(group)

        groups_map[key]["items"].append(
            {
                "size_name": "יחידות" if is_simple else item.size_name,
                "quantity": item.quantity,
                "line_total": "{:.2f}".format(item.get_line_total()),
            }
        )
        groups_map[key]["group_total"] += item.get_line_total()

    return grouped_items


def _nav_context():
    """Common navigation context shared by all views."""
    return {
        "all_categories": WhiteCategory.objects.all(),
        "standalone_subcategories": WhiteSubcategory.objects.filter(category__isnull=True),
    }


def _cart_count(request):
    user = get_current_catalog_user(request)
    if not user:
        return 0
    try:
        cart = WhiteCart.objects.get(user=user, status=WhiteCart.STATUS_ACTIVE)
        return cart.get_item_count()
    except WhiteCart.DoesNotExist:
        return 0


def catalog_home(request):
    """Main white catalog page showing all categories and standalone subcategories."""
    categories = WhiteCategory.objects.filter(show_products_on_homepage=False)
    standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True).prefetch_related("images")
    category_homepage_subcategories = WhiteSubcategory.objects.filter(
        category__show_products_on_homepage=True
    ).select_related("category").prefetch_related("images").order_by(
        "category__order", "category__name", "order", "name"
    )
    context = {
        "categories": categories,
        "standalone_subcategories": standalone_subcategories,
        "homepage_subcategories": list(category_homepage_subcategories) + list(standalone_subcategories),
        "all_categories": WhiteCategory.objects.all(),
        "cart_count": _cart_count(request),
    }
    return render(request, "white_catalog/catalog_home.html", context)


def category_detail(request, category_slug):
    """Category detail page showing subcategories."""
    category = get_object_or_404(WhiteCategory, slug=category_slug)
    context = {
        **_nav_context(),
        "category": category,
        "subcategories": category.subcategories.all(),
        "cart_count": _cart_count(request),
    }
    return render(request, "white_catalog/category_detail.html", context)


def _subcategory_detail_context(request, subcategory, category=None):
    """Build context for subcategory detail views."""
    catalog_user = get_current_catalog_user(request)
    show_variant_ordering = bool(catalog_user and subcategory.is_orderable and subcategory.has_order_variants)
    show_simple_ordering = bool(catalog_user and subcategory.is_orderable and not subcategory.has_order_variants)

    # Build variants JSON grouped by fabric_type for the ordering widget
    variants_data = []
    pack_types_data = []
    simple_cart_quantity = 0
    active_cart = None
    if catalog_user:
        try:
            active_cart = WhiteCart.objects.prefetch_related("items").get(
                user=catalog_user,
                status=WhiteCart.STATUS_ACTIVE,
            )
        except WhiteCart.DoesNotExist:
            active_cart = None

    if show_variant_ordering:
        cart_qty_map = {}
        if active_cart:
            cart_qty_map = {
                (item.variant_id, item.pack_type_id): item.quantity
                for item in active_cart.items.filter(
                    product=subcategory,
                    variant__isnull=False,
                    pack_type__isnull=False,
                )
            }

        pack_types_data = [
            {"pack_id": pt.pk, "pack_name": pt.name, "pack_qty": pt.quantity}
            for pt in WhitePackType.objects.filter(is_active=True)
        ]

        fabric_map = {}
        for variant in (subcategory.variants
                        .filter(is_active=True)
                        .select_related("fabric_type", "size_type")):
            fid = variant.fabric_type_id
            if fid not in fabric_map:
                fabric_map[fid] = {
                    "fabric_id": fid,
                    "name": variant.fabric_type.name,
                    "sizes": [],
                }
            effective_price = variant.unit_price if variant.unit_price is not None else subcategory.unit_price
            fabric_map[fid]["sizes"].append({
                "variant_id": variant.id,
                "size_name": variant.size_type.name,
                "unit_price": str(effective_price) if effective_price is not None else None,
                "cart_quantities": {
                    str(pt["pack_id"]): cart_qty_map.get((variant.id, pt["pack_id"]), 0)
                    for pt in pack_types_data
                },
            })
        variants_data = list(fabric_map.values())
    elif show_simple_ordering and active_cart:
        simple_item = (
            active_cart.items.filter(
                product=subcategory,
                variant__isnull=True,
                pack_type__isnull=True,
            )
            .first()
        )
        if simple_item:
            simple_cart_quantity = simple_item.quantity

    return {
        **_nav_context(),
        "category": category,
        "subcategory": subcategory,
        "subcategory_images": subcategory.images.all(),
        "catalog_user": catalog_user,
        "show_variant_ordering": show_variant_ordering,
        "show_simple_ordering": show_simple_ordering,
        "variants_data": variants_data,
        "pack_types_data": pack_types_data,
        "simple_cart_quantity": simple_cart_quantity,
        "cart_count": _cart_count(request),
    }


def subcategory_detail(request, category_slug, subcategory_slug):
    """Subcategory detail page with image gallery."""
    category = get_object_or_404(WhiteCategory, slug=category_slug)
    subcategory = get_object_or_404(WhiteSubcategory, category=category, slug=subcategory_slug)
    return render(request, "white_catalog/subcategory_detail.html",
                  _subcategory_detail_context(request, subcategory, category))


def standalone_subcategory_detail(request, subcategory_slug):
    """Standalone subcategory detail page (without category)."""
    subcategory = get_object_or_404(WhiteSubcategory, slug=subcategory_slug, category__isnull=True)
    return render(request, "white_catalog/subcategory_detail.html",
                  _subcategory_detail_context(request, subcategory))


def login_view(request):
	"""Login view for white catalog users."""
	if request.method == "POST":
		username = request.POST.get("username", "").strip()
		password = request.POST.get("password", "")
		
		if not username or not password:
			messages.error(request, "נא למלא שם משתמש וסיסמא")
		else:
			try:
				user = WhiteCatalogUser.objects.get(username=username, is_active=True)
				password_ok = user.check_password(password)
			except WhiteCatalogUser.DoesNotExist:
				user = None
				password_ok = False

			if not password_ok:
				django_user = authenticate(request, username=username, password=password)
				if django_user and django_user.is_active and (django_user.is_staff or django_user.is_superuser):
					user = _sync_admin_to_catalog_user(django_user, raw_password=password)
					password_ok = bool(user)

			if password_ok and user:
				_catalog_session_login(request, user)

				# Update last login time
				user.last_login = timezone.now()
				user.save(update_fields=['last_login'])

				# Log activity
				try:
					WhiteCatalogUserActivity.objects.create(
						user=user,
						ip_address=get_client_ip(request),
						user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
						page_url=request.path[:500]
					)
				except Exception:
					pass  # Don't let logging errors break the login flow

				# Update activity timestamp
				user.update_activity()

				messages.success(request, f"ברוך הבא, {user.company_name}!")

				# Redirect to next page or home
				next_url = request.GET.get("next") or request.POST.get("next") or "white_catalog:home"
				return redirect(next_url)

			messages.error(request, "שם משתמש או סיסמא שגויים")
	
	# Get all categories for navigation
	all_categories = WhiteCategory.objects.all()
	standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
	
	context = {
		"all_categories": all_categories,
		"standalone_subcategories": standalone_subcategories,
	}
	return render(request, "white_catalog/login.html", context)


def logout_view(request):
    """Logout view for white catalog users."""
    for key in ("white_catalog_user_id", "white_catalog_username", "white_catalog_company_name"):
        request.session.pop(key, None)
    messages.success(request, "התנתקת בהצלחה")
    return redirect("white_catalog:home")


# ---------------------------------------------------------------------------
# Cart views
# ---------------------------------------------------------------------------

@require_POST
@require_catalog_login
def cart_add(request):
    """Add/update items in the cart from the product ordering form."""
    user = get_current_catalog_user(request)
    cart = get_or_create_active_cart(user)

    want_json = request.POST.get("format") == "json"
    product_id = request.POST.get("product_id")
    simple_quantity_raw = request.POST.get("simple_quantity")

    if product_id and simple_quantity_raw is not None:
        try:
            product = WhiteSubcategory.objects.get(pk=product_id, is_orderable=True)
        except (WhiteSubcategory.DoesNotExist, TypeError, ValueError):
            if want_json:
                return JsonResponse({"ok": False, "error": "המוצר לא זמין להזמנה"}, status=400)
            messages.error(request, "המוצר לא זמין להזמנה")
            return redirect(request.POST.get("next") or "white_catalog:cart")

        if product.has_order_variants:
            if want_json:
                return JsonResponse({"ok": False, "error": "למוצר זה יש להזין הזמנה לפי גרסאות ומארזים"}, status=400)
            messages.error(request, "למוצר זה יש להזין הזמנה לפי גרסאות ומארזים")
            return redirect(request.POST.get("next") or "white_catalog:cart")

        try:
            quantity = int((simple_quantity_raw or "").strip() or 0)
        except (TypeError, ValueError, AttributeError):
            quantity = 0

        if quantity < 0:
            quantity = 0

        if product.unit_price is None:
            if want_json:
                return JsonResponse({"ok": False, "error": "מחיר לא זמין"}, status=400)
            messages.error(request, "מחיר לא זמין")
            return redirect(request.POST.get("next") or "white_catalog:cart")

        existing_item = (
            WhiteCartItem.objects.filter(
                cart=cart,
                product=product,
                variant__isnull=True,
                pack_type__isnull=True,
            )
            .first()
        )

        added = 1 if quantity > 0 else 0
        if quantity == 0:
            if existing_item:
                existing_item.delete()
        elif existing_item:
            existing_item.quantity = quantity
            existing_item.price_at_add = product.unit_price
            existing_item.save(update_fields=["quantity", "price_at_add", "updated"])
        else:
            WhiteCartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                price_at_add=product.unit_price,
            )

        if want_json:
            return JsonResponse(
                {
                    "ok": True,
                    "added": added,
                    "cart_count": cart.get_item_count(),
                    "message": (
                        "דף ההזמנה עודכן"
                        if added
                        else "המוצר הוסר מדף ההזמנה"
                    ),
                }
            )

        if added:
            messages.success(request, "דף ההזמנה עודכן")
        else:
            messages.info(request, "המוצר הוסר מדף ההזמנה")
        return redirect(request.POST.get("next") or "white_catalog:cart")

    pack_type_id = request.POST.get("pack_type_id")
    try:
        pack_type = WhitePackType.objects.get(pk=pack_type_id, is_active=True)
    except (WhitePackType.DoesNotExist, TypeError, ValueError):
        if want_json:
            return JsonResponse({"ok": False, "error": "נא לבחור סוג אריזה"}, status=400)
        messages.error(request, "נא לבחור סוג אריזה")
        return redirect(request.POST.get("next") or "white_catalog:cart")

    added = 0
    for key, value in request.POST.items():
        if not key.startswith("qty_"):
            continue
        try:
            variant_id = key[4:]
            raw = (value or "").strip()
            quantity = 0 if raw == "" else int(raw)
        except (ValueError, TypeError, AttributeError):
            continue

        if quantity < 0:
            continue

        try:
            variant = WhiteProductVariant.objects.select_related("product").get(
                pk=variant_id, is_active=True
            )
        except WhiteProductVariant.DoesNotExist:
            continue

        if not variant.product.is_orderable or not variant.product.has_order_variants:
            continue

        effective_price = variant.unit_price if variant.unit_price is not None else variant.product.unit_price
        if effective_price is None:
            continue

        # Price per pack = unit_price × units in pack
        price_per_pack = effective_price * pack_type.quantity

        if quantity == 0:
            WhiteCartItem.objects.filter(cart=cart, variant=variant, pack_type=pack_type).delete()
        else:
            WhiteCartItem.objects.update_or_create(
                cart=cart,
                variant=variant,
                pack_type=pack_type,
                defaults={
                    "product": variant.product,
                    "quantity": quantity,
                    "price_at_add": price_per_pack,
                }
            )
            added += 1

    if want_json:
        return JsonResponse(
            {
                "ok": True,
                "added": added,
                "cart_count": cart.get_item_count(),
                "message": (
                    f"דף ההזמנה עודכן — {added} פריטים נוספו"
                    if added
                    else "לא נוספו פריטים להזמנה"
                ),
            }
        )

    if added:
        messages.success(request, f"דף ההזמנה עודכן — {added} פריטים נוספו")
    else:
        messages.info(request, "לא נוספו פריטים להזמנה")

    return redirect(request.POST.get("next") or "white_catalog:cart")


@require_catalog_login
def cart_view(request):
    """Display the current cart contents."""
    context = {**_nav_context(), **_build_cart_page_context(request)}
    return render(request, "white_catalog/cart.html", context)


@require_catalog_login
def cart_drawer(request):
    """HTML fragment for the cart side panel (AJAX)."""
    context = {
        **_nav_context(),
        **_build_cart_page_context(request),
        "drawer_mode": True,
    }
    return render(request, "white_catalog/cart_drawer_ajax.html", context)


@require_POST
@require_catalog_login
def cart_update(request):
    """Update quantity or remove a single cart item."""
    user = get_current_catalog_user(request)
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")  # "update" or "remove"
    variant_id = request.POST.get("variant_id")
    pack_type_id = request.POST.get("pack_type_id")
    product_id = request.POST.get("product_id")
    is_ajax = request.POST.get("format") == "json"

    if settings.DEBUG:
        logger.warning(
            "cart_update start user=%s item_id=%s action=%s quantity=%s is_ajax=%s path=%s",
            getattr(user, "username", None),
            item_id,
            action,
            request.POST.get("quantity"),
            is_ajax,
            request.path,
        )

    item = None
    pack_type = None
    variant = None
    product = None
    if item_id:
        try:
            item = WhiteCartItem.objects.select_related("cart").get(pk=item_id, cart__user=user, cart__status=WhiteCart.STATUS_ACTIVE)
        except WhiteCartItem.DoesNotExist:
            if settings.DEBUG:
                logger.warning(
                    "cart_update missing item user=%s item_id=%s action=%s",
                    getattr(user, "username", None),
                    item_id,
                    action,
                )
            messages.error(request, "הפריט לא נמצא")
            return redirect("white_catalog:cart")
    elif action == "update" and variant_id and pack_type_id:
        cart = get_or_create_active_cart(user)
        try:
            variant = WhiteProductVariant.objects.select_related("product").get(
                pk=variant_id,
                is_active=True,
            )
            pack_type = WhitePackType.objects.get(pk=pack_type_id, is_active=True)
        except (WhiteProductVariant.DoesNotExist, WhitePackType.DoesNotExist, TypeError, ValueError):
            if is_ajax:
                return JsonResponse({"status": "error", "error": "הפריט לא נמצא"}, status=400)
            messages.error(request, "הפריט לא נמצא")
            return redirect("white_catalog:cart")
        item = (
            WhiteCartItem.objects.select_related("cart")
            .filter(cart=cart, variant=variant, pack_type=pack_type)
            .first()
        )
    elif action == "update" and product_id:
        cart = get_or_create_active_cart(user)
        try:
            product = WhiteSubcategory.objects.get(pk=product_id, is_orderable=True, has_order_variants=False)
        except (WhiteSubcategory.DoesNotExist, TypeError, ValueError):
            if is_ajax:
                return JsonResponse({"status": "error", "error": "הפריט לא נמצא"}, status=400)
            messages.error(request, "הפריט לא נמצא")
            return redirect("white_catalog:cart")
        item = (
            WhiteCartItem.objects.select_related("cart")
            .filter(cart=cart, product=product, variant__isnull=True, pack_type__isnull=True)
            .first()
        )
    else:
        if is_ajax:
            return JsonResponse({"status": "error", "error": "הפריט לא נמצא"}, status=400)
        messages.error(request, "הפריט לא נמצא")
        return redirect("white_catalog:cart")

    if action == "remove":
        cart_obj = item.cart
        cart_pk = cart_obj.pk
        item.delete()
        if is_ajax:
            try:
                cart = WhiteCart.objects.get(pk=cart_pk)
                ct = "{:.2f}".format(cart.get_total())
                cc = cart.get_item_count()
            except WhiteCart.DoesNotExist:
                ct = "0.00"
                cc = 0
            if settings.DEBUG:
                logger.warning(
                    "cart_update removed item_id=%s cart_total=%s cart_count=%s",
                    item_id,
                    ct,
                    cc,
                )
            return JsonResponse({"status": "removed", "cart_total": ct, "cart_count": cc})
        messages.success(request, "הפריט הוסר מההזמנה")
    elif action == "update":
        try:
            qty = int(request.POST.get("quantity", 0))
        except ValueError:
            qty = 0
        if qty <= 0:
            if not item:
                cart_obj = get_or_create_active_cart(user)
                cart_pk = cart_obj.pk
                if is_ajax:
                    return JsonResponse({
                        "status": "noop",
                        "cart_total": "{:.2f}".format(cart_obj.get_total()),
                        "cart_count": cart_obj.get_item_count(),
                    })
                return redirect("white_catalog:cart")
            cart_obj = item.cart
            cart_pk = cart_obj.pk
            item.delete()
            if is_ajax:
                try:
                    cart = WhiteCart.objects.get(pk=cart_pk)
                    ct = "{:.2f}".format(cart.get_total())
                    cc = cart.get_item_count()
                except WhiteCart.DoesNotExist:
                    ct = "0.00"
                    cc = 0
                if settings.DEBUG:
                    logger.warning(
                        "cart_update qty<=0 removed item_id=%s cart_total=%s cart_count=%s",
                        item_id,
                        ct,
                        cc,
                    )
                return JsonResponse({"status": "removed", "cart_total": ct, "cart_count": cc})
            messages.success(request, "הפריט הוסר מההזמנה")
        else:
            if not item:
                if product:
                    effective_price = product.unit_price
                else:
                    effective_price = variant.unit_price if variant.unit_price is not None else variant.product.unit_price
                if effective_price is None:
                    if is_ajax:
                        return JsonResponse({"status": "error", "error": "מחיר לא זמין"}, status=400)
                    messages.error(request, "מחיר לא זמין")
                    return redirect("white_catalog:cart")
                if product:
                    item = WhiteCartItem.objects.create(
                        cart=cart,
                        product=product,
                        quantity=qty,
                        price_at_add=effective_price,
                    )
                else:
                    item, _ = WhiteCartItem.objects.update_or_create(
                        cart=cart,
                        variant=variant,
                        pack_type=pack_type,
                        defaults={
                            "product": variant.product,
                            "quantity": qty,
                            "price_at_add": effective_price * pack_type.quantity,
                        },
                    )
            else:
                item.quantity = qty
                item.save(update_fields=["quantity", "updated"])
            if is_ajax:
                line_total = item.price_at_add * qty
                cart_total = "{:.2f}".format(item.cart.get_total())
                cart_count = item.cart.get_item_count()
                if settings.DEBUG:
                    logger.warning(
                        "cart_update saved item_id=%s qty=%s line_total=%s cart_total=%s cart_count=%s",
                        item.id,
                        qty,
                        "{:.2f}".format(line_total),
                        cart_total,
                        cart_count,
                    )
                return JsonResponse({
                    "status": "ok",
                    "item_id": item.id,
                    "line_total": "{:.2f}".format(line_total),
                    "cart_total": cart_total,
                    "cart_count": cart_count,
                })

    return redirect("white_catalog:cart")


@require_POST
@require_catalog_login
def cart_clear(request):
    """Remove all items from the active cart."""
    user = get_current_catalog_user(request)
    WhiteCart.objects.filter(user=user, status=WhiteCart.STATUS_ACTIVE).delete()
    messages.success(request, "ההזמנה נוקתה בהצלחה")
    return redirect("white_catalog:cart")


# ---------------------------------------------------------------------------
# Checkout & Orders
# ---------------------------------------------------------------------------

@require_catalog_login
def checkout(request):
    """Submit the order (POST only). GET redirects to cart."""
    if request.method != "POST":
        return redirect("white_catalog:cart")

    user = get_current_catalog_user(request)
    try:
        cart = WhiteCart.objects.prefetch_related(
            "items__product", "items__variant__fabric_type", "items__variant__size_type", "items__pack_type"
        ).get(user=user, status=WhiteCart.STATUS_ACTIVE)
    except WhiteCart.DoesNotExist:
        messages.error(request, "דף ההזמנה ריק")
        return redirect("white_catalog:cart")

    if not cart.items.exists():
        messages.error(request, "דף ההזמנה ריק")
        return redirect("white_catalog:cart")

    notes = request.POST.get("notes", "").strip()
    total = cart.get_total()

    order = WhiteOrder.objects.create(
        user=user,
        cart=cart,
        status=WhiteOrder.STATUS_PENDING,
        notes=notes,
        total_amount=total,
    )

    for item in cart.items.select_related("product", "variant__fabric_type", "variant__size_type", "pack_type").all():
        WhiteOrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            product_name=item.product.name,
            variant_name=item.display_variant_name,
            size_name=item.display_size_name,
            pack_type_name=item.display_pack_name,
            pack_quantity=item.pack_type.quantity if item.pack_type_id else 1,
            quantity=item.quantity,
            unit_price=item.price_at_add,
        )

    cart.status = WhiteCart.STATUS_SUBMITTED
    cart.save(update_fields=["status", "updated"])

    messages.success(request, f"ההזמנה {order.order_number} התקבלה בהצלחה!")
    return redirect("white_catalog:order_confirm", order_number=order.order_number)


@require_catalog_login
def order_confirm(request, order_number):
    """Order confirmation page."""
    user = get_current_catalog_user(request)
    order = get_object_or_404(
        WhiteOrder.objects.prefetch_related(
            "items__product__images",
            "items__variant__fabric_type",
            "items__variant__size_type",
        ),
        order_number=order_number,
        user=user,
    )
    context = {
        **_nav_context(),
        "order": order,
        "grouped_items": _build_order_grouped_items(order),
        "cart_count": _cart_count(request),
    }
    return render(request, "white_catalog/order_confirm.html", context)


@require_catalog_login
def order_list(request):
    """List of all orders for the logged-in user."""
    user = get_current_catalog_user(request)
    orders = WhiteOrder.objects.filter(user=user).prefetch_related("items").order_by("-created")
    context = {
        **_nav_context(),
        "orders": orders,
        "cart_count": _cart_count(request),
    }
    return render(request, "white_catalog/order_list.html", context)

