import json
from decimal import Decimal
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


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_current_catalog_user(request):
    """Return the logged-in WhiteCatalogUser or None."""
    user_id = request.session.get("white_catalog_user_id")
    if not user_id:
        return None
    try:
        return WhiteCatalogUser.objects.get(pk=user_id, is_active=True)
    except WhiteCatalogUser.DoesNotExist:
        return None


def require_catalog_login(view_func):
    """Decorator: redirect unauthenticated users to login page."""
    def wrapper(request, *args, **kwargs):
        if not get_current_catalog_user(request):
            return redirect(f"/white-catalog/login/?next={request.path}")
        return view_func(request, *args, **kwargs)
    return wrapper


def get_or_create_active_cart(user):
    """Return the user's active cart, creating one if needed."""
    cart, _ = WhiteCart.objects.get_or_create(user=user, status=WhiteCart.STATUS_ACTIVE)
    return cart


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
    categories = WhiteCategory.objects.all()
    standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
    context = {
        "categories": categories,
        "standalone_subcategories": standalone_subcategories,
        "all_categories": categories,
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

    # Build variants JSON grouped by fabric_type for the ordering widget
    variants_data = []
    if subcategory.is_orderable and catalog_user:
        fabric_map = {}  # fabric_type_id -> {id, name, sizes[]}
        for variant in (subcategory.variants
                        .filter(is_active=True)
                        .select_related("fabric_type", "size_type")
                        .prefetch_related("pack_prices__pack_type")):
            fid = variant.fabric_type_id
            if fid not in fabric_map:
                fabric_map[fid] = {
                    "fabric_id": fid,
                    "name": variant.fabric_type.name,
                    "sizes": [],
                }
            pack_prices_data = [
                {
                    "pack_id": pp.pack_type_id,
                    "pack_name": pp.pack_type.name,
                    "price": str(pp.price),
                }
                for pp in variant.pack_prices.all()
            ]
            fabric_map[fid]["sizes"].append({
                "variant_id": variant.id,
                "size_name": variant.size_type.name,
                "pack_prices": pack_prices_data,
            })
        variants_data = list(fabric_map.values())

    return {
        **_nav_context(),
        "category": category,
        "subcategory": subcategory,
        "subcategory_images": subcategory.images.all(),
        "catalog_user": catalog_user,
        "variants_json": json.dumps(variants_data, ensure_ascii=False),
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
				if user.check_password(password):
					# Login successful - store user ID in session
					request.session["white_catalog_user_id"] = user.id
					request.session["white_catalog_username"] = user.username
					request.session["white_catalog_company_name"] = user.company_name
					
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
				else:
					messages.error(request, "שם משתמש או סיסמא שגויים")
			except WhiteCatalogUser.DoesNotExist:
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

    added = 0
    for key, value in request.POST.items():
        # Field names: qty_{variant_id}_{pack_type_id}
        if not key.startswith("qty_"):
            continue
        try:
            _, variant_id, pack_id = key.split("_")
            quantity = int(value)
        except (ValueError, AttributeError):
            continue

        if quantity < 0:
            continue

        try:
            variant = WhiteProductVariant.objects.select_related("product").get(pk=variant_id, is_active=True)
            pack_type = WhitePackType.objects.get(pk=pack_id, is_active=True)
            price_obj = WhiteVariantPackPrice.objects.get(variant=variant, pack_type=pack_type)
        except (WhiteProductVariant.DoesNotExist, WhitePackType.DoesNotExist, WhiteVariantPackPrice.DoesNotExist):
            continue

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
                    "price_at_add": price_obj.price,
                }
            )
            added += 1

    if added:
        messages.success(request, f"הסל עודכן — {added} פריטים נוספו")
    else:
        messages.info(request, "לא נוספו פריטים לסל")

    next_url = request.POST.get("next") or "white_catalog:cart"
    return redirect(next_url)


@require_catalog_login
def cart_view(request):
    """Display the current cart contents."""
    user = get_current_catalog_user(request)
    try:
        cart = WhiteCart.objects.prefetch_related(
            "items__product", "items__variant", "items__variant_size", "items__pack_type"
        ).get(user=user, status=WhiteCart.STATUS_ACTIVE)
    except WhiteCart.DoesNotExist:
        cart = None

    context = {
        **_nav_context(),
        "cart": cart,
        "cart_count": cart.get_item_count() if cart else 0,
    }
    return render(request, "white_catalog/cart.html", context)


@require_POST
@require_catalog_login
def cart_update(request):
    """Update quantity or remove a single cart item."""
    user = get_current_catalog_user(request)
    item_id = request.POST.get("item_id")
    action = request.POST.get("action")  # "update" or "remove"

    try:
        item = WhiteCartItem.objects.select_related("cart").get(pk=item_id, cart__user=user, cart__status=WhiteCart.STATUS_ACTIVE)
    except WhiteCartItem.DoesNotExist:
        messages.error(request, "הפריט לא נמצא")
        return redirect("white_catalog:cart")

    if action == "remove":
        item.delete()
        messages.success(request, "הפריט הוסר מהסל")
    elif action == "update":
        try:
            qty = int(request.POST.get("quantity", 0))
        except ValueError:
            qty = 0
        if qty <= 0:
            item.delete()
            messages.success(request, "הפריט הוסר מהסל")
        else:
            item.quantity = qty
            item.save(update_fields=["quantity", "updated"])
            messages.success(request, "הכמות עודכנה")

    return redirect("white_catalog:cart")


@require_POST
@require_catalog_login
def cart_clear(request):
    """Remove all items from the active cart."""
    user = get_current_catalog_user(request)
    WhiteCart.objects.filter(user=user, status=WhiteCart.STATUS_ACTIVE).delete()
    messages.success(request, "הסל רוקן בהצלחה")
    return redirect("white_catalog:cart")


# ---------------------------------------------------------------------------
# Checkout & Orders
# ---------------------------------------------------------------------------

@require_catalog_login
def checkout(request):
    """Review cart and submit the order."""
    user = get_current_catalog_user(request)
    try:
        cart = WhiteCart.objects.prefetch_related(
            "items__product", "items__variant", "items__variant_size", "items__pack_type"
        ).get(user=user, status=WhiteCart.STATUS_ACTIVE)
    except WhiteCart.DoesNotExist:
        messages.error(request, "הסל שלך ריק")
        return redirect("white_catalog:cart")

    if not cart.items.exists():
        messages.error(request, "הסל שלך ריק")
        return redirect("white_catalog:cart")

    if request.method == "POST":
        notes = request.POST.get("notes", "").strip()
        total = cart.get_total()

        order = WhiteOrder.objects.create(
            user=user,
            cart=cart,
            status=WhiteOrder.STATUS_PENDING,
            notes=notes,
            total_amount=total,
        )

        for item in cart.items.select_related("product", "variant", "variant_size", "pack_type").all():
            WhiteOrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                variant_name=item.variant.name,
                size_name=item.variant_size.size_name,
                pack_type_name=item.pack_type.name,
                pack_quantity=item.pack_type.quantity,
                quantity=item.quantity,
                unit_price=item.price_at_add,
            )

        cart.status = WhiteCart.STATUS_SUBMITTED
        cart.save(update_fields=["status", "updated"])

        messages.success(request, f"ההזמנה {order.order_number} התקבלה בהצלחה!")
        return redirect("white_catalog:order_confirm", order_number=order.order_number)

    context = {
        **_nav_context(),
        "cart": cart,
        "cart_count": cart.get_item_count(),
    }
    return render(request, "white_catalog/checkout.html", context)


@require_catalog_login
def order_confirm(request, order_number):
    """Order confirmation page."""
    user = get_current_catalog_user(request)
    order = get_object_or_404(WhiteOrder, order_number=order_number, user=user)
    context = {
        **_nav_context(),
        "order": order,
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

