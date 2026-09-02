"""Views for the Molly catalog.

Most pages are gated behind a Molly catalog session login. Mockup share pages
(`/mockups/<id>/share/`) are public view-only. There is no fallback to Django
staff/superuser. Catalog prices exist for staff invoicing but are never shown
to Molly.
"""

import logging
from functools import wraps

import resend
from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import (
    MollyCart,
    MollyCartItem,
    MollyCatalogUser,
    MollyCatalogUserActivity,
    MollyCategory,
    MollyLabelColor,
    MollyMockup,
    MollyMockupLayer,
    MollyMockupProduct,
    MollyOrder,
    MollyOrderItem,
    MollyProduct,
    MollyVariant,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

SESSION_USER_ID = "molly_catalog_user_id"
SESSION_USERNAME = "molly_catalog_username"
SESSION_DISPLAY_NAME = "molly_catalog_display_name"


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _login_session(request, user):
    request.session[SESSION_USER_ID] = user.id
    request.session[SESSION_USERNAME] = user.username
    request.session[SESSION_DISPLAY_NAME] = user.display_name


def get_current_molly_user(request):
    """Return the active Molly user from the session, or None."""
    user_id = request.session.get(SESSION_USER_ID)
    if not user_id:
        return None
    try:
        return MollyCatalogUser.objects.get(pk=user_id, is_active=True)
    except MollyCatalogUser.DoesNotExist:
        return None


def _safe_molly_next(next_url):
    """Allow only relative /molly/ paths as post-login redirects."""
    if not next_url:
        return "molly_catalog:home"
    next_url = str(next_url).strip()
    if next_url.startswith("/molly/") and "://" not in next_url and "\\" not in next_url:
        return next_url
    return "molly_catalog:home"


def require_molly_login(view_func):
    """Decorator: redirect unauthenticated users to the Molly login page."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not get_current_molly_user(request):
            from urllib.parse import quote

            next_target = request.get_full_path()
            return redirect(
                reverse("molly_catalog:login") + "?next=" + quote(next_target, safe="")
            )
        return view_func(request, *args, **kwargs)

    return wrapper


def _get_or_create_active_cart(user):
    cart, _ = MollyCart.objects.get_or_create(user=user, status=MollyCart.STATUS_ACTIVE)
    return cart


def _cart_count(request):
    user = get_current_molly_user(request)
    if not user:
        return 0
    try:
        cart = MollyCart.objects.get(user=user, status=MollyCart.STATUS_ACTIVE)
    except MollyCart.DoesNotExist:
        return 0
    return cart.get_item_count()


def _nav_context():
    """Shared navigation data: categories + standalone products."""
    return {
        "all_categories": MollyCategory.objects.all(),
        "standalone_products": MollyProduct.objects.filter(category__isnull=True),
    }


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def login_view(request):
    """Render the login form and authenticate POST submissions."""
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        if not username or not password:
            messages.error(request, "נא למלא שם משתמש וסיסמא")
        else:
            try:
                user = MollyCatalogUser.objects.get(username=username, is_active=True)
            except MollyCatalogUser.DoesNotExist:
                user = None

            if user and user.check_password(password):
                _login_session(request, user)
                user.last_login = timezone.now()
                user.save(update_fields=["last_login"])
                try:
                    MollyCatalogUserActivity.objects.create(
                        user=user,
                        ip_address=_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                        page_url=request.path[:500],
                    )
                except Exception:
                    pass
                user.update_activity()
                messages.success(request, f"ברוכה הבאה, {user.display_name}!")
                next_url = _safe_molly_next(
                    request.GET.get("next") or request.POST.get("next")
                )
                return redirect(next_url)

            messages.error(request, "שם משתמש או סיסמא שגויים")

    return render(request, "molly_catalog/login.html", {})


def logout_view(request):
    for key in (SESSION_USER_ID, SESSION_USERNAME, SESSION_DISPLAY_NAME):
        request.session.pop(key, None)
    messages.success(request, "התנתקת בהצלחה")
    return redirect("molly_catalog:login")


# ---------------------------------------------------------------------------
# Browse views (all gated)
# ---------------------------------------------------------------------------

@require_molly_login
def catalog_home(request):
    """Home page: categories + standalone products."""
    categories = MollyCategory.objects.all().prefetch_related("products")
    standalone_products = MollyProduct.objects.filter(category__isnull=True).prefetch_related("images")
    context = {
        **_nav_context(),
        "categories": categories,
        "standalone_products": standalone_products,
        "cart_count": _cart_count(request),
    }
    return render(request, "molly_catalog/catalog_home.html", context)


@require_molly_login
def category_detail(request, category_slug):
    category = get_object_or_404(MollyCategory, slug=category_slug)
    context = {
        **_nav_context(),
        "category": category,
        "products": category.products.all().prefetch_related("images"),
        "cart_count": _cart_count(request),
    }
    return render(request, "molly_catalog/category_detail.html", context)


def _build_variants_data(product, cart=None):
    """Return JSON-serializable variant data + lookup dicts for the product page.

    Variants are grouped by (background_color × print × fabric). The frontend
    uses three <select> elements; the JS narrows the active variant by matching
    the chosen attribute IDs.
    """
    qs = product.variants.filter(is_active=True).select_related(
        "background_color", "print_design", "fabric_type", "default_label_color"
    )

    # Existing cart quantities, keyed by variant_id (summed across label-color choices).
    cart_qty_map = {}
    if cart is not None:
        for item in cart.items.filter(product=product, variant__isnull=False):
            cart_qty_map[item.variant_id] = cart_qty_map.get(item.variant_id, 0) + item.quantity

    background_colors = {}
    print_designs = {}
    fabric_types = {}
    variants = []
    for v in qs:
        background_colors.setdefault(v.background_color_id, {
            "id": v.background_color_id,
            "name": v.background_color.name,
            "hex_color": v.background_color.hex_color,
            "swatch_url": v.background_color.swatch_image.url if v.background_color.swatch_image else "",
        })
        print_designs.setdefault(v.print_design_id, {
            "id": v.print_design_id,
            "name": v.print_design.name,
            "preview_url": v.print_design.preview_image.url if v.print_design.preview_image else "",
        })
        fabric_types.setdefault(v.fabric_type_id, {
            "id": v.fabric_type_id,
            "name": v.fabric_type.name,
        })
        variants.append({
            "id": v.id,
            "name": v.display_name,
            "background_color_id": v.background_color_id,
            "background_color_name": v.background_color.name,
            "print_design_id": v.print_design_id,
            "print_design_name": v.print_design.name,
            "fabric_type_id": v.fabric_type_id,
            "fabric_type_name": v.fabric_type.name,
            "default_label_color_id": v.default_label_color_id,
            "default_label_color_name": v.default_label_color.name if v.default_label_color_id else "",
            "default_label_color_hex": v.default_label_color.hex_color if v.default_label_color_id else "",
            "image_url": v.get_image_url() or (product.get_main_image() or ""),
            "sku": v.sku,
            "cart_quantity": cart_qty_map.get(v.id, 0),
        })

    return {
        "background_colors": list(background_colors.values()),
        "print_designs": list(print_designs.values()),
        "fabric_types": list(fabric_types.values()),
        "variants": variants,
    }


def _product_detail_context(request, product, category=None):
    user = get_current_molly_user(request)
    active_cart = None
    simple_cart_quantity = 0
    if user:
        try:
            active_cart = MollyCart.objects.prefetch_related("items").get(
                user=user, status=MollyCart.STATUS_ACTIVE
            )
        except MollyCart.DoesNotExist:
            active_cart = None

    variants_data = {"background_colors": [], "print_designs": [], "fabric_types": [], "variants": []}
    if product.has_variants:
        variants_data = _build_variants_data(product, cart=active_cart)
    elif active_cart:
        simple_item = active_cart.items.filter(
            product=product, variant__isnull=True
        ).first()
        if simple_item:
            simple_cart_quantity = simple_item.quantity

    label_color_options = [
        {
            "id": lc.id,
            "name": lc.name,
            "hex_color": lc.hex_color,
            "swatch_url": lc.swatch_image.url if lc.swatch_image else "",
        }
        for lc in product.available_label_colors.filter(is_active=True).order_by("order", "name")
    ]

    return {
        **_nav_context(),
        "category": category,
        "product": product,
        "product_images": product.images.all(),
        "variants_data": variants_data,
        "label_color_options": label_color_options,
        "simple_cart_quantity": simple_cart_quantity,
        "cart_count": _cart_count(request),
    }


@require_molly_login
def product_detail(request, product_slug, category_slug=None):
    """Product detail page. Used both for standalone and category-bound products.

    Lookup is by product slug (unique). If the URL's category segment is missing
    or stale, redirect to the canonical get_absolute_url() instead of 404.
    """
    from urllib.parse import unquote

    from django.utils.text import slugify

    product = (
        MollyProduct.objects.select_related("category")
        .filter(slug=product_slug)
        .first()
    )
    if product is None:
        # Slug may have drifted from the name; recover by slugifying names.
        for candidate in MollyProduct.objects.select_related("category").all():
            if slugify(candidate.name, allow_unicode=True) == product_slug:
                product = candidate
                break
    if product is None:
        raise Http404("No MollyProduct matches the given query.")

    canonical = product.get_absolute_url()
    current = unquote(request.path)
    if current.rstrip("/") != unquote(canonical).rstrip("/"):
        return redirect(canonical)

    return render(
        request,
        "molly_catalog/product_detail.html",
        _product_detail_context(request, product, product.category),
    )


# ---------------------------------------------------------------------------
# Cart views
# ---------------------------------------------------------------------------

def _build_cart_page_context(request):
    """Materialize cart items for cart page / drawer."""
    user = get_current_molly_user(request)
    if not user:
        return {"cart": None, "cart_items": [], "cart_count": 0}

    try:
        cart = MollyCart.objects.prefetch_related(
            "items__product__images",
            "items__product__category",
            "items__variant__background_color",
            "items__variant__print_design",
            "items__variant__fabric_type",
            "items__variant__default_label_color",
            "items__selected_label_color",
        ).get(user=user, status=MollyCart.STATUS_ACTIVE)
    except MollyCart.DoesNotExist:
        cart = None

    cart_items = []
    if cart:
        for item in cart.items.all().order_by("created"):
            v = item.variant
            effective = item.effective_label_color()
            cart_items.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "product_url": item.product.get_absolute_url(),
                "variant_id": item.variant_id or "",
                "variant_name": item.display_variant_name(),
                "background_color": v.background_color.name if v else "",
                "print_design": v.print_design.name if v else "",
                "fabric_type": v.fabric_type.name if v else "",
                "label_color": effective.name if effective else "",
                "label_color_hex": effective.hex_color if effective else "",
                "image_url": item.get_image_url() or "",
                "quantity": item.quantity,
                "sku": v.sku if v else "",
            })

    return {
        "cart": cart,
        "cart_items": cart_items,
        "cart_count": cart.get_item_count() if cart else 0,
    }


@require_molly_login
def cart_view(request):
    context = {**_nav_context(), **_build_cart_page_context(request)}
    return render(request, "molly_catalog/cart.html", context)


@require_molly_login
def cart_drawer(request):
    context = {**_nav_context(), **_build_cart_page_context(request), "drawer_mode": True}
    return render(request, "molly_catalog/cart_drawer_ajax.html", context)


@require_POST
@require_molly_login
def cart_add(request):
    """Add a single product/variant to the active cart."""
    user = get_current_molly_user(request)
    cart = _get_or_create_active_cart(user)
    want_json = request.POST.get("format") == "json"

    product_id = request.POST.get("product_id")
    variant_id = request.POST.get("variant_id") or None
    label_color_id = request.POST.get("label_color_id") or None
    try:
        quantity = int(request.POST.get("quantity") or 0)
    except (TypeError, ValueError):
        quantity = 0

    if quantity < 0:
        quantity = 0

    try:
        product = MollyProduct.objects.get(pk=product_id, is_orderable=True)
    except (MollyProduct.DoesNotExist, TypeError, ValueError):
        if want_json:
            return JsonResponse({"ok": False, "error": "המוצר לא נמצא"}, status=400)
        messages.error(request, "המוצר לא נמצא")
        return redirect(request.POST.get("next") or "molly_catalog:cart")

    if product.has_variants:
        if not variant_id:
            if want_json:
                return JsonResponse({"ok": False, "error": "נא לבחור צבע, הדפס וסוג בד"}, status=400)
            messages.error(request, "נא לבחור צבע, הדפס וסוג בד")
            return redirect(request.POST.get("next") or "molly_catalog:cart")
        try:
            variant = MollyVariant.objects.select_related("product", "default_label_color").get(
                pk=variant_id, is_active=True, product=product
            )
        except (MollyVariant.DoesNotExist, TypeError, ValueError):
            if want_json:
                return JsonResponse({"ok": False, "error": "הואריאנט לא נמצא"}, status=400)
            messages.error(request, "הואריאנט לא נמצא")
            return redirect(request.POST.get("next") or "molly_catalog:cart")
    else:
        variant = None

    # Resolve label color: prefer customer's choice if it's one of the product's
    # available options. Fall back to the variant's default.
    selected_label_color = None
    if variant is not None:
        if label_color_id:
            try:
                selected_label_color = product.available_label_colors.get(
                    pk=label_color_id, is_active=True
                )
            except MollyLabelColor.DoesNotExist:
                selected_label_color = None
        if selected_label_color is None:
            selected_label_color = variant.default_label_color

    if quantity == 0:
        # Treat 0 as "remove from cart"
        if variant is None:
            MollyCartItem.objects.filter(cart=cart, product=product, variant__isnull=True).delete()
        else:
            MollyCartItem.objects.filter(
                cart=cart, variant=variant, selected_label_color=selected_label_color
            ).delete()
        message = "הפריט הוסר מההזמנה"
        if want_json:
            return JsonResponse({
                "ok": True,
                "added": 0,
                "cart_count": cart.get_item_count(),
                "message": message,
            })
        messages.info(request, message)
        return redirect(request.POST.get("next") or "molly_catalog:cart")

    if variant is None:
        item, created = MollyCartItem.objects.update_or_create(
            cart=cart,
            product=product,
            variant=None,
            selected_label_color=None,
            defaults={"quantity": quantity},
        )
    else:
        item, created = MollyCartItem.objects.update_or_create(
            cart=cart,
            variant=variant,
            selected_label_color=selected_label_color,
            defaults={"product": product, "quantity": quantity},
        )

    message = "ההזמנה עודכנה"
    if want_json:
        return JsonResponse({
            "ok": True,
            "added": 1,
            "cart_count": cart.get_item_count(),
            "message": message,
        })
    messages.success(request, message)
    return redirect(request.POST.get("next") or "molly_catalog:cart")


@require_POST
@require_molly_login
def cart_add_bulk(request):
    """Add/update several variants of one product in a single submit.

    The product page renders one row per variant with its own quantity and
    label-color picker. Each row contributes a (variant_id, label_color_id,
    quantity) triple via parallel POST lists. We enforce a single cart line
    per variant: quantity 0 removes the variant, switching the label updates
    the same line rather than duplicating it.
    """
    user = get_current_molly_user(request)
    cart = _get_or_create_active_cart(user)
    want_json = request.POST.get("format") == "json"

    try:
        product = MollyProduct.objects.get(
            pk=request.POST.get("product_id"), is_orderable=True
        )
    except (MollyProduct.DoesNotExist, TypeError, ValueError):
        if want_json:
            return JsonResponse({"ok": False, "error": "המוצר לא נמצא"}, status=400)
        messages.error(request, "המוצר לא נמצא")
        return redirect(request.POST.get("next") or "molly_catalog:cart")

    variant_ids = request.POST.getlist("variant_id")
    label_ids = request.POST.getlist("label_color_id")
    quantities = request.POST.getlist("quantity")

    changed = 0
    quantities_by_variant = {}
    for vid, lid, qraw in zip(variant_ids, label_ids, quantities):
        variant = MollyVariant.objects.select_related("default_label_color").filter(
            pk=vid, is_active=True, product=product
        ).first()
        if not variant:
            continue

        try:
            qty = int(qraw or 0)
        except (TypeError, ValueError):
            qty = 0

        # Resolve label: prefer customer choice among the product's options,
        # then fall back to the variant default.
        label = None
        if lid:
            label = product.available_label_colors.filter(
                pk=lid, is_active=True
            ).first()
        if label is None:
            label = variant.default_label_color

        if qty <= 0:
            removed = MollyCartItem.objects.filter(cart=cart, variant=variant).delete()
            if removed[0]:
                changed += 1
            quantities_by_variant[variant.id] = 0
        else:
            # Keep a single line per variant: drop stale label lines first.
            MollyCartItem.objects.filter(cart=cart, variant=variant).exclude(
                selected_label_color=label
            ).delete()
            MollyCartItem.objects.update_or_create(
                cart=cart,
                variant=variant,
                selected_label_color=label,
                defaults={"product": product, "quantity": qty},
            )
            changed += 1
            quantities_by_variant[variant.id] = qty

    if want_json:
        return JsonResponse({
            "ok": True,
            "changed": changed,
            "cart_count": cart.get_item_count(),
            "quantities": quantities_by_variant,
        })

    if changed:
        messages.success(request, "ההזמנה עודכנה")
    else:
        messages.info(request, "לא נבחרה כמות לאף ואריאנט")
    return redirect(request.POST.get("next") or "molly_catalog:cart")


@require_POST
@require_molly_login
def cart_update(request):
    """Update quantity or remove an existing cart item."""
    user = get_current_molly_user(request)
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")
    is_ajax = request.POST.get("format") == "json"

    try:
        item = MollyCartItem.objects.select_related("cart").get(
            pk=item_id, cart__user=user, cart__status=MollyCart.STATUS_ACTIVE
        )
    except (MollyCartItem.DoesNotExist, TypeError, ValueError):
        if is_ajax:
            return JsonResponse({"status": "error", "error": "הפריט לא נמצא"}, status=400)
        messages.error(request, "הפריט לא נמצא")
        return redirect("molly_catalog:cart")

    cart = item.cart

    if action == "remove":
        item.delete()
        if is_ajax:
            return JsonResponse({
                "status": "removed",
                "cart_count": cart.get_item_count(),
            })
        messages.success(request, "הפריט הוסר מההזמנה")
        return redirect("molly_catalog:cart")

    if action == "update":
        try:
            qty = int(request.POST.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            item.delete()
            if is_ajax:
                return JsonResponse({
                    "status": "removed",
                    "cart_count": cart.get_item_count(),
                })
            messages.success(request, "הפריט הוסר מההזמנה")
            return redirect("molly_catalog:cart")

        item.quantity = qty
        item.save(update_fields=["quantity", "updated"])
        if is_ajax:
            return JsonResponse({
                "status": "ok",
                "item_id": item.id,
                "quantity": item.quantity,
                "cart_count": cart.get_item_count(),
            })
        messages.success(request, "ההזמנה עודכנה")
        return redirect("molly_catalog:cart")

    if is_ajax:
        return JsonResponse({"status": "error", "error": "פעולה לא חוקית"}, status=400)
    messages.error(request, "פעולה לא חוקית")
    return redirect("molly_catalog:cart")


@require_POST
@require_molly_login
def cart_clear(request):
    user = get_current_molly_user(request)
    MollyCart.objects.filter(user=user, status=MollyCart.STATUS_ACTIVE).delete()
    messages.success(request, "ההזמנה נוקתה")
    return redirect("molly_catalog:cart")


# ---------------------------------------------------------------------------
# Checkout & order views
# ---------------------------------------------------------------------------

def send_molly_order_notification(order):
    """Email the manufacturer a summary when Molly submits an order."""
    try:
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set, skipping Molly order email")
            return
        resend.api_key = settings.RESEND_API_KEY

        lines = []
        for item in order.items.all():
            # Product name first so the manufacturer knows WHAT to make, then
            # the full variant breakdown (fabric / background / print).
            parts = [item.product_name or "מוצר"]
            variant_desc = item.display_variant_name()
            if variant_desc and variant_desc != "ללא ואריאנט":
                parts.append(variant_desc)
            if item.label_color_name:
                parts.append(f"תווית: {item.label_color_name}")
            if item.variant_sku:
                parts.append(f'מק"ט: {item.variant_sku}')
            parts.append(f"כמות: {item.quantity}")
            lines.append("- " + " | ".join(parts))

        body = (
            "התקבלה הזמנה חדשה מקטלוג מולי!\n\n"
            f"מספר הזמנה: {order.order_number}\n"
            f"לקוחה: {order.user.display_name}\n"
            f"תאריך: {order.created:%d/%m/%Y %H:%M}\n"
            f'סה"כ יחידות: {order.get_total_quantity()}\n\n'
            "פריטים:\n" + "\n".join(lines) + "\n\n"
            f"הערות מולי: {order.notes or 'אין'}\n"
        )

        resend.Emails.send({
            "from": "Arye Textile <onboarding@resend.dev>",
            "to": [settings.MOLLY_ORDER_NOTIFY_EMAIL],
            "subject": f"הזמנה חדשה ממולי: {order.order_number}",
            "text": body,
        })
        logger.info("Molly order email sent for %s", order.order_number)
    except Exception:
        logger.exception("Failed to send Molly order notification")


@require_molly_login
def checkout(request):
    """Submit the active cart as a new MollyOrder. POST only; GET → cart."""
    if request.method != "POST":
        return redirect("molly_catalog:cart")

    user = get_current_molly_user(request)
    try:
        cart = MollyCart.objects.prefetch_related(
            "items__product",
            "items__variant__background_color",
            "items__variant__print_design",
            "items__variant__fabric_type",
            "items__variant__default_label_color",
            "items__selected_label_color",
        ).get(user=user, status=MollyCart.STATUS_ACTIVE)
    except MollyCart.DoesNotExist:
        messages.error(request, "ההזמנה ריקה")
        return redirect("molly_catalog:cart")

    if not cart.items.exists():
        messages.error(request, "ההזמנה ריקה")
        return redirect("molly_catalog:cart")

    notes = (request.POST.get("notes") or "").strip()

    order = MollyOrder.objects.create(
        user=user,
        cart=cart,
        status=MollyOrder.STATUS_PENDING,
        notes=notes,
    )

    for item in cart.items.all():
        v = item.variant
        effective_label = item.effective_label_color()
        order_item = MollyOrderItem(
            order=order,
            product=item.product,
            variant=v,
            product_name=item.product.name,
            background_color_name=v.background_color.name if v else "",
            print_design_name=v.print_design.name if v else "",
            fabric_type_name=v.fabric_type.name if v else "",
            label_color_name=(effective_label.name if effective_label else ""),
            variant_sku=v.sku if v else "",
            quantity=item.quantity,
        )
        order_item.apply_unit_price(item.product.sale_price)
        order_item.save()

    cart.status = MollyCart.STATUS_SUBMITTED
    cart.save(update_fields=["status", "updated"])

    send_molly_order_notification(order)

    messages.success(request, f"ההזמנה {order.order_number} התקבלה!")
    return redirect("molly_catalog:order_confirm", order_number=order.order_number)


@require_molly_login
def order_confirm(request, order_number):
    user = get_current_molly_user(request)
    order = get_object_or_404(
        MollyOrder.objects.prefetch_related("items__product__images", "items__variant"),
        order_number=order_number,
        user=user,
    )
    context = {
        **_nav_context(),
        "order": order,
        "cart_count": _cart_count(request),
    }
    return render(request, "molly_catalog/order_confirm.html", context)


# ---------------------------------------------------------------------------
# Mockup studio (הדמיות)
# ---------------------------------------------------------------------------

@require_molly_login
def mockup_studio(request):
    """Mockup studio page: pick a product, upload a print, position & save."""
    user = get_current_molly_user(request)
    products = MollyMockupProduct.objects.filter(is_active=True)
    mockups = MollyMockup.objects.filter(user=user).select_related("mockup_product")
    context = {
        **_nav_context(),
        "mockup_products": products,
        "saved_mockups": mockups,
        "cart_count": _cart_count(request),
    }
    return render(request, "molly_catalog/mockup_studio.html", context)


@require_molly_login
def mockup_product_image(request, product_id):
    """Serve a mockup product image from the site's own origin.

    In production media lives on a CDN (different origin), which taints the
    editor's canvas and breaks CSS mask-image. Proxying the image through the
    app keeps it same-origin so background masking and saving work.
    """
    import mimetypes

    from django.http import HttpResponse

    product = get_object_or_404(MollyMockupProduct, pk=product_id, is_active=True)
    with product.image.open("rb") as f:
        content = f.read()
    content_type = mimetypes.guess_type(product.image.name)[0] or "image/png"
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


# Hebrew / English color names for offline prompt parsing (no API key).
_LOCAL_RECOLOR_COLORS = {
    "ורוד": ("#f4a0c0", "ורוד"),
    "פוקסיה": ("#e91e8c", "פוקסיה"),
    "אדום": ("#e53935", "אדום"),
    "בורדו": ("#800020", "בורדו"),
    "כתום": ("#fb8c00", "כתום"),
    "צהוב": ("#fdd835", "צהוב"),
    "זהב": ("#d4af37", "זהב"),
    "ירוק": ("#43a047", "ירוק"),
    "מנטה": ("#80cbc4", "מנטה"),
    "תכלת": ("#4fc3f7", "תכלת"),
    "כחול": ("#1e88e5", "כחול"),
    "סגול": ("#8e24aa", "סגול"),
    "לבנדר": ("#b39ddb", "לבנדר"),
    "חום": ("#8d6e63", "חום"),
    "בז": ("#d7ccc8", "בז"),
    "שחור": ("#212121", "שחור"),
    "אפור": ("#9e9e9e", "אפור"),
    "לבן": ("#fafafa", "לבן"),
    "pink": ("#f4a0c0", "pink"),
    "red": ("#e53935", "red"),
    "orange": ("#fb8c00", "orange"),
    "yellow": ("#fdd835", "yellow"),
    "green": ("#43a047", "green"),
    "blue": ("#1e88e5", "blue"),
    "purple": ("#8e24aa", "purple"),
    "black": ("#212121", "black"),
    "white": ("#fafafa", "white"),
    "brown": ("#8d6e63", "brown"),
}


def _local_recolor_from_prompt(prompt: str):
    """Return (hex, label) from a simple color keyword in the prompt, or None."""
    text = (prompt or "").strip()
    if not text:
        return None
    text_l = text.lower()
    # Prefer longer keys first (e.g. לבנדר before shorter overlaps)
    for key, value in sorted(_LOCAL_RECOLOR_COLORS.items(), key=lambda kv: -len(kv[0])):
        if key.isascii():
            if key.lower() in text_l:
                return value
        elif key in text:
            return value
    return None


def _openai_recolor_from_prompt(prompt: str):
    """Ask OpenAI for a target hex color. Raises on failure."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    system = (
        "You parse short Hebrew or English requests about recoloring a seamless "
        "textile pattern motif (trees, leaves, flowers, animals, etc.). "
        "Return ONLY JSON with keys: target_hex (string like #rrggbb), "
        "label (short Hebrew or English color name). "
        "Do not change shape, layout, or garment — color only. "
        "If the user does not ask for a color change, return "
        '{"target_hex":"","label":"","error":"not_a_recolor"}.'
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    import json

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    hex_color = (data.get("target_hex") or "").strip()
    label = (data.get("label") or "").strip()
    if data.get("error") == "not_a_recolor" or not hex_color:
        return None
    if not hex_color.startswith("#"):
        hex_color = "#" + hex_color
    if len(hex_color) not in (4, 7):
        raise ValueError("invalid hex from model")
    return hex_color, label or hex_color


@require_POST
@require_molly_login
def mockup_ai_recolor(request):
    """Parse an all-over recolor prompt into a target hex (OpenAI + local fallback)."""
    import json

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (TypeError, ValueError, UnicodeDecodeError):
        body = {}
    prompt = (body.get("prompt") or request.POST.get("prompt") or "").strip()
    if not prompt:
        return JsonResponse({"ok": False, "error": "נא לכתוב מה לשנות"}, status=400)
    if len(prompt) > 400:
        return JsonResponse({"ok": False, "error": "הפרומפט ארוך מדי"}, status=400)

    source = "local"
    parsed = None
    if getattr(settings, "OPENAI_API_KEY", ""):
        try:
            parsed = _openai_recolor_from_prompt(prompt)
            source = "openai"
        except Exception:
            logger.exception("OpenAI recolor parse failed; trying local fallback")
            parsed = None

    if not parsed:
        parsed = _local_recolor_from_prompt(prompt)
        source = "local"

    if not parsed:
        return JsonResponse(
            {
                "ok": False,
                "error": "לא הצלחתי להבין איזה צבע לשנות. נסי למשל: שנה את העצים לוורוד",
            },
            status=400,
        )

    target_hex, label = parsed
    return JsonResponse({
        "ok": True,
        "target_hex": target_hex,
        "label": label,
        "source": source,
        "mode": "all_ink",
    })


def _mockup_layer_transform_payload(transform):
    """Normalize saved layer transform JSON for the studio editor."""
    t = transform if isinstance(transform, dict) else {}
    mode = t.get("mode") if t.get("mode") in ("focused", "allover") else "focused"
    payload = {
        "name": (t.get("name") or "שכבה")[:120],
        "mode": mode,
        "x": t.get("x", 0.5),
        "y": t.get("y", 0.45),
        "width": t.get("width", 0.35),
        "tile": t.get("tile", 0.25),
        "density": t.get("density", 1),
        "offsetX": t.get("offsetX", 0),
        "offsetY": t.get("offsetY", 0),
        "visible": True if t.get("visible") is None else bool(t.get("visible")),
        "blend": t.get("blend") or "multiply",
    }
    if t.get("baseWidth") is not None:
        payload["baseWidth"] = t.get("baseWidth")
    if t.get("baseTile") is not None:
        payload["baseTile"] = t.get("baseTile")
    if t.get("colorSlots") is not None:
        payload["colorSlots"] = t.get("colorSlots")
    if t.get("activeColorSlot") is not None:
        payload["activeColorSlot"] = t.get("activeColorSlot")
    return payload


def _serve_mockup_owned_image(request, mockup_id, image_field):
    """Same-origin image bytes for a mockup the current user owns."""
    import mimetypes

    from django.http import HttpResponse

    user = get_current_molly_user(request)
    mockup = get_object_or_404(MollyMockup, pk=mockup_id, user=user)
    if not image_field:
        raise Http404()
    with image_field.open("rb") as f:
        content = f.read()
    content_type = mimetypes.guess_type(image_field.name)[0] or "image/png"
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "private, max-age=300"
    return response


def _serve_mockup_result_bytes(mockup, *, public=False, download=False):
    """Return HttpResponse with mockup result image bytes."""
    import mimetypes

    from django.http import HttpResponse

    if not mockup.result_image:
        raise Http404()
    with mockup.result_image.open("rb") as f:
        content = f.read()
    content_type = mimetypes.guess_type(mockup.result_image.name)[0] or "image/png"
    response = HttpResponse(content, content_type=content_type)
    if public:
        response["Cache-Control"] = "public, max-age=600"
    else:
        response["Cache-Control"] = "private, max-age=300"
    if download:
        response["Content-Disposition"] = (
            f'attachment; filename="mockup-{mockup.pk}.png"'
        )
    return response


@require_GET
def mockup_share(request, mockup_id):
    """Public view-only page for a specific mockup (no login required)."""
    mockup = get_object_or_404(MollyMockup, pk=mockup_id)
    if not mockup.result_image:
        raise Http404()

    from urllib.parse import quote

    user = get_current_molly_user(request)
    can_edit = bool(user and mockup.user_id == user.id)
    edit_path = reverse("molly_catalog:mockups") + f"?open={mockup.id}"
    if user:
        edit_href = edit_path
    else:
        edit_href = reverse("molly_catalog:login") + "?next=" + quote(edit_path, safe="")

    image_path = reverse(
        "molly_catalog:mockup_share_image", kwargs={"mockup_id": mockup.id}
    )
    share_path = reverse("molly_catalog:mockup_share", kwargs={"mockup_id": mockup.id})

    og_w = None
    og_h = None
    try:
        from PIL import Image as PilImage

        with mockup.result_image.open("rb") as f:
            with PilImage.open(f) as im:
                og_w, og_h = im.size
    except Exception:
        pass

    context = {
        **_nav_context(),
        "mockup": mockup,
        "can_edit": can_edit,
        "edit_href": edit_href,
        "image_url": image_path,
        "absolute_image_url": request.build_absolute_uri(image_path),
        "absolute_share_url": request.build_absolute_uri(share_path),
        "og_image_width": og_w,
        "og_image_height": og_h,
        "cart_count": _cart_count(request) if user else 0,
        "is_logged_in": bool(user),
    }
    return render(request, "molly_catalog/mockup_share.html", context)


@require_GET
def mockup_share_image(request, mockup_id):
    """Public result image for share pages / WhatsApp preview (no login)."""
    mockup = get_object_or_404(MollyMockup, pk=mockup_id)
    return _serve_mockup_result_bytes(mockup, public=True)


@require_GET
@require_molly_login
def mockup_detail(request, mockup_id):
    """Return a saved mockup + layers so the studio can reopen it for editing."""
    user = get_current_molly_user(request)
    mockup = get_object_or_404(
        MollyMockup.objects.select_related("mockup_product").prefetch_related("layers"),
        pk=mockup_id,
        user=user,
    )
    product = mockup.mockup_product
    if not product or not product.is_active:
        return JsonResponse(
            {"ok": False, "error": "המוצר של ההדמיה אינו זמין יותר לעריכה"},
            status=400,
        )

    layers_out = []
    db_layers = list(mockup.layers.all())
    if db_layers:
        for layer in db_layers:
            item = _mockup_layer_transform_payload(layer.transform_data)
            item["image_url"] = reverse(
                "molly_catalog:mockup_layer_image",
                kwargs={"mockup_id": mockup.id, "layer_id": layer.id},
            )
            layers_out.append(item)
    elif mockup.print_image:
        root = mockup.transform_data if isinstance(mockup.transform_data, dict) else {}
        legacy_list = root.get("layers") if isinstance(root.get("layers"), list) else []
        legacy_t = legacy_list[0] if legacy_list and isinstance(legacy_list[0], dict) else root
        item = _mockup_layer_transform_payload(legacy_t)
        item["image_url"] = reverse(
            "molly_catalog:mockup_legacy_print_image",
            kwargs={"mockup_id": mockup.id},
        )
        layers_out.append(item)
    else:
        return JsonResponse(
            {"ok": False, "error": "לא נמצאו שכבות בהדמיה זו"},
            status=400,
        )

    real_w = product.real_width_cm
    return JsonResponse({
        "ok": True,
        "mockup_id": mockup.id,
        "name": mockup.display_name,
        "product_id": product.id,
        "product_name": product.name,
        "product_image_url": reverse(
            "molly_catalog:mockup_product_image",
            kwargs={"product_id": product.id},
        ),
        "real_width_cm": float(real_w) if real_w is not None else None,
        "layers": layers_out,
    })


@require_GET
@require_molly_login
def mockup_layer_image(request, mockup_id, layer_id):
    """Serve one saved layer image same-origin (for canvas / masks)."""
    user = get_current_molly_user(request)
    layer = get_object_or_404(
        MollyMockupLayer.objects.select_related("mockup"),
        pk=layer_id,
        mockup_id=mockup_id,
        mockup__user=user,
    )
    return _serve_mockup_owned_image(request, mockup_id, layer.image)


@require_GET
@require_molly_login
def mockup_legacy_print_image(request, mockup_id):
    """Serve legacy single-print mockup image same-origin."""
    user = get_current_molly_user(request)
    mockup = get_object_or_404(MollyMockup, pk=mockup_id, user=user)
    if not mockup.print_image:
        raise Http404()
    return _serve_mockup_owned_image(request, mockup_id, mockup.print_image)


@require_GET
@require_molly_login
def mockup_result_image(request, mockup_id):
    """Serve saved result image same-origin (download / preview without Spaces navigation)."""
    user = get_current_molly_user(request)
    mockup = get_object_or_404(MollyMockup, pk=mockup_id, user=user)
    return _serve_mockup_result_bytes(
        mockup, public=False, download=bool(request.GET.get("download"))
    )


@require_POST
@require_molly_login
def mockup_save(request):
    """Save a mockup: base product id + layer files + composited result PNG.

    If mockup_id is provided and owned by the user, update that record instead
    of creating a new one (continue-editing flow).
    """
    import json

    user = get_current_molly_user(request)

    try:
        product = MollyMockupProduct.objects.get(
            pk=request.POST.get("product_id"), is_active=True
        )
    except (MollyMockupProduct.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "המוצר לא נמצא"}, status=400)

    result_image = request.FILES.get("result_image")
    layer_images = request.FILES.getlist("layer_images")
    if not result_image or not layer_images:
        return JsonResponse({"ok": False, "error": "חסרות תמונות שכבה או תמונת הדמיה"}, status=400)

    max_size = 15 * 1024 * 1024  # 15MB
    if result_image.size > max_size or any(f.size > max_size for f in layer_images):
        return JsonResponse({"ok": False, "error": "הקובץ גדול מדי (מקסימום 15MB)"}, status=400)

    try:
        layers_data = json.loads(request.POST.get("layers_data") or "[]")
        if not isinstance(layers_data, list):
            layers_data = []
    except (TypeError, ValueError):
        layers_data = []

    existing = None
    raw_id = (request.POST.get("mockup_id") or "").strip()
    if raw_id:
        try:
            existing = MollyMockup.objects.get(pk=int(raw_id), user=user)
        except (MollyMockup.DoesNotExist, TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "ההדמיה לעדכון לא נמצאה"}, status=404)

    mockup_name = (request.POST.get("name") or "").strip()[:200]
    if not existing and not mockup_name:
        return JsonResponse({"ok": False, "error": "נא לתת שם להדמיה"}, status=400)

    if existing:
        for layer in existing.layers.all():
            layer.image.delete(save=False)
            layer.delete()
        if existing.result_image:
            existing.result_image.delete(save=False)
        if existing.print_image:
            existing.print_image.delete(save=False)
            existing.print_image = None
        existing.mockup_product = product
        existing.product_name = product.name
        if mockup_name:
            existing.name = mockup_name
        existing.result_image = result_image
        existing.transform_data = {"layers": layers_data}
        existing.save()
        mockup = existing
        updated = True
    else:
        mockup = MollyMockup.objects.create(
            user=user,
            mockup_product=product,
            product_name=product.name,
            name=mockup_name,
            result_image=result_image,
            transform_data={"layers": layers_data},
        )
        updated = False

    for i, layer_file in enumerate(layer_images):
        transform = layers_data[i] if i < len(layers_data) and isinstance(layers_data[i], dict) else {}
        MollyMockupLayer.objects.create(
            mockup=mockup,
            image=layer_file,
            transform_data=transform,
            order=i,
        )

    return JsonResponse({
        "ok": True,
        "updated": updated,
        "mockup_id": mockup.id,
        "result_url": mockup.result_image.url,
        "download_url": reverse(
            "molly_catalog:mockup_result_image",
            kwargs={"mockup_id": mockup.id},
        ) + "?download=1",
        "load_url": reverse(
            "molly_catalog:mockup_detail", kwargs={"mockup_id": mockup.id}
        ),
        "share_url": reverse(
            "molly_catalog:mockup_share", kwargs={"mockup_id": mockup.id}
        ),
        "name": mockup.display_name,
        "product_name": mockup.product_name,
        "created": mockup.created.strftime("%d/%m/%Y %H:%M"),
        "delete_url": reverse(
            "molly_catalog:mockup_delete", kwargs={"mockup_id": mockup.id}
        ),
    })


@require_POST
@require_molly_login
def mockup_delete(request, mockup_id):
    """Delete one of the current user's saved mockups."""
    user = get_current_molly_user(request)
    try:
        mockup = MollyMockup.objects.get(pk=mockup_id, user=user)
    except MollyMockup.DoesNotExist:
        return JsonResponse({"ok": False, "error": "ההדמיה לא נמצאה"}, status=404)

    for layer in mockup.layers.all():
        layer.image.delete(save=False)
    if mockup.print_image:
        mockup.print_image.delete(save=False)
    mockup.result_image.delete(save=False)
    mockup.delete()
    return JsonResponse({"ok": True})


@require_molly_login
def order_list(request):
    user = get_current_molly_user(request)
    orders = MollyOrder.objects.filter(user=user).prefetch_related("items").order_by("-created")
    context = {
        **_nav_context(),
        "orders": orders,
        "cart_count": _cart_count(request),
    }
    return render(request, "molly_catalog/order_list.html", context)
