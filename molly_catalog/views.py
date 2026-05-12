"""Views for the Molly catalog.

Everything is gated behind a Molly catalog session login. There is no public
browsing and no fallback to Django staff/superuser – the catalog is fully
private. Prices are never shown or computed anywhere.
"""

import logging
from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    MollyCart,
    MollyCartItem,
    MollyCatalogUser,
    MollyCatalogUserActivity,
    MollyCategory,
    MollyLabelColor,
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


def require_molly_login(view_func):
    """Decorator: redirect unauthenticated users to the Molly login page."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not get_current_molly_user(request):
            return redirect(f"/molly/login/?next={request.path}")
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
                next_url = request.GET.get("next") or request.POST.get("next") or "molly_catalog:home"
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
            "background_color_id": v.background_color_id,
            "print_design_id": v.print_design_id,
            "fabric_type_id": v.fabric_type_id,
            "default_label_color_id": v.default_label_color_id,
            "default_label_color_name": v.default_label_color.name if v.default_label_color_id else "",
            "default_label_color_hex": v.default_label_color.hex_color if v.default_label_color_id else "",
            "image_url": v.get_image_url() or "",
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
    """Product detail page. Used both for standalone and category-bound products."""
    if category_slug:
        category = get_object_or_404(MollyCategory, slug=category_slug)
        product = get_object_or_404(
            MollyProduct, category=category, slug=product_slug
        )
    else:
        category = None
        product = get_object_or_404(
            MollyProduct, slug=product_slug, category__isnull=True
        )
    return render(
        request,
        "molly_catalog/product_detail.html",
        _product_detail_context(request, product, category),
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
        MollyOrderItem.objects.create(
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

    cart.status = MollyCart.STATUS_SUBMITTED
    cart.save(update_fields=["status", "updated"])

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
