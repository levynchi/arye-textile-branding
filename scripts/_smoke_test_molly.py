"""Smoke test for the Molly catalog – created during initial scaffolding.

Run with: python scripts/_smoke_test_molly.py
"""
import os
import re
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "arye_site.settings.local")
django.setup()

from urllib.parse import urlencode  # noqa: E402
import urllib.request  # noqa: E402
import http.cookiejar  # noqa: E402

from molly_catalog.models import (  # noqa: E402
    MollyBackgroundColor,
    MollyCatalogUser,
    MollyCategory,
    MollyFabricType,
    MollyLabelColor,
    MollyPrintDesign,
    MollyProduct,
    MollyVariant,
)


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def seed():
    section("1. Seeding data")

    user, _ = MollyCatalogUser.objects.get_or_create(
        username="molly_test",
        defaults={"display_name": "מולי (בדיקה)"},
    )
    user.set_password("test1234")
    user.is_active = True
    user.save()
    print(f"  user: {user}")

    bc_white, _ = MollyBackgroundColor.objects.get_or_create(
        name="לבן", defaults={"hex_color": "#ffffff"}
    )
    bc_pink, _ = MollyBackgroundColor.objects.get_or_create(
        name="ורוד", defaults={"hex_color": "#ffc8dd"}
    )
    pd_stars, _ = MollyPrintDesign.objects.get_or_create(
        name="כוכבים קטנים שחורים"
    )
    ft_fleece, _ = MollyFabricType.objects.get_or_create(name="פליז")
    ft_jersey, _ = MollyFabricType.objects.get_or_create(name="טריקו")
    lc_black, _ = MollyLabelColor.objects.get_or_create(
        name="שחור", defaults={"hex_color": "#000000"}
    )
    lc_white, _ = MollyLabelColor.objects.get_or_create(
        name="לבן-תווית", defaults={"hex_color": "#ffffff"}
    )
    print(f"  attributes: 2 colors, 1 print, 2 fabrics, 2 label colors")

    cat, _ = MollyCategory.objects.get_or_create(name="שמיכות", defaults={"slug": "blankets"})
    prod, _ = MollyProduct.objects.get_or_create(
        name="שמיכה רגילה",
        defaults={"is_orderable": True, "has_variants": True, "category": cat, "slug": "blanket-classic"},
    )
    print(f"  product: {prod} (slug={prod.slug})")

    created = 0
    for c in (bc_white, bc_pink):
        for f in (ft_fleece, ft_jersey):
            default_label = lc_white if c == bc_white else lc_black
            v, was_created = MollyVariant.objects.get_or_create(
                product=prod,
                background_color=c,
                print_design=pd_stars,
                fabric_type=f,
                defaults={"default_label_color": default_label},
            )
            if not was_created and v.default_label_color_id != default_label.id:
                v.default_label_color = default_label
                v.save(update_fields=["default_label_color"])
            if was_created:
                created += 1
    print(f"  variants created: {created} (total now: {prod.variants.count()})")

    # Wire up the product's selectable label colors (the new feature).
    prod.available_label_colors.set([lc_black, lc_white])
    print(f"  product available label colors: {[l.name for l in prod.available_label_colors.all()]}")
    return user, prod, cat, lc_black, lc_white


def http_flow(user, prod, cat, lc_black, lc_white):
    section("2. HTTP flow via real dev server")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPRedirectHandler())

    def fetch(path, data=None, allow_redirects=True):
        url = f"http://127.0.0.1:8000{path}"
        if data is not None and isinstance(data, dict):
            data = urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
        try:
            resp = opener.open(req, timeout=10)
            return resp.getcode(), resp.geturl(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.geturl(), (e.read().decode("utf-8", errors="replace") if e.fp else "")

    # 1. GET login -> grab CSRF
    code, url, body = fetch("/molly/login/")
    print(f"  GET /molly/login/ -> {code} {url}")
    m = re.search(r"csrfmiddlewaretoken[^>]+value=\"([^\"]+)\"", body)
    assert m, "no CSRF token on login page"
    csrf = m.group(1)
    print(f"  csrf token captured (len={len(csrf)})")

    # 2. POST login
    code, url, body = fetch(
        "/molly/login/",
        data={"username": "molly_test", "password": "test1234", "csrfmiddlewaretoken": csrf},
    )
    print(f"  POST /molly/login/ -> {code} {url}")
    assert "/molly/login" not in url, f"login failed, still at: {url}"

    # 3. GET home (should show catalog content for logged-in user)
    code, url, body = fetch("/molly/")
    print(f"  GET /molly/ -> {code} {url}")
    assert code == 200
    assert "קטלוג מולי" in body
    assert cat.slug in body, f"category slug {cat.slug} not in home"
    print("  OK: home page renders with category card")

    # 3b. GET category page (should list the product)
    code, url, body = fetch(f"/molly/{cat.slug}/")
    print(f"  GET /molly/{cat.slug}/ -> {code}")
    assert code == 200
    assert prod.slug in body, f"product slug {prod.slug} not in category page"
    print("  OK: category page lists the product")

    # 4. GET product detail - the page now renders a single empty variant row
    #    with an expandable picker plus a "+ add another row" button. The full
    #    list of variants is embedded as JSON for the JS to render on demand.
    path = f"/molly/{cat.slug}/{prod.slug}/"
    code, url, body = fetch(path)
    print(f"  GET {path} -> {code}")
    assert code == 200
    assert "molly-variant-builder" in body, "product page must render the variant builder shell"
    assert "mollyVariantRowTemplate" in body, "the row template must be present for the JS to clone"
    assert "mollyAddRowButton" in body, "the page must render the + add-row button"
    # The previous direct-list and dropdown approaches must both be gone:
    assert "molly-variant-list" not in body
    assert "mollyFabricSelect" not in body
    # The full variants list is shipped to the page as JSON for the picker.
    assert "mollyVariantsData" in body, "variants_data JSON must be in the page"
    for v in prod.variants.all():
        assert f'"id": {v.id}' in body, f"variant id {v.id} must appear inside mollyVariantsData JSON"
    assert "mollyLabelColorOptionsData" in body, "product page must expose label-color options"
    print("  OK: product page renders one empty row + variant picker template + add-row button")

    # 5. POST cart_add with first variant. Pick the NON-default label so we
    #    can confirm Molly's choice is what gets stored, not the variant default.
    variant = prod.variants.first()
    if variant.default_label_color_id == lc_black.id:
        chosen_label = lc_white
    else:
        chosen_label = lc_black
    m = re.search(r"csrfmiddlewaretoken[^>]+value=\"([^\"]+)\"", body)
    csrf = m.group(1)
    code, url, body = fetch(
        "/molly/cart/add/",
        data={
            "product_id": prod.id,
            "variant_id": variant.id,
            "label_color_id": chosen_label.id,
            "quantity": 3,
            "csrfmiddlewaretoken": csrf,
        },
    )
    print(f"  POST /molly/cart/add/ variant={variant.id} label={chosen_label.name} qty=3 -> {code} {url}")

    # 6. GET cart - verify Molly's CHOSEN label shows, not the variant default
    code, url, body = fetch("/molly/cart/")
    print(f"  GET /molly/cart/ -> {code}")
    assert "3" in body  # the qty appears somewhere
    assert prod.name in body
    assert chosen_label.name in body, (
        f"cart should display the chosen label color ({chosen_label.name}) not the default"
    )
    print(f"  OK: cart shows added item with chosen label color ({chosen_label.name})")

    # 7. POST checkout
    m = re.search(r"csrfmiddlewaretoken[^>]+value=\"([^\"]+)\"", body)
    csrf = m.group(1)
    code, url, body = fetch(
        "/molly/checkout/",
        data={"notes": "בדיקה אוטומטית", "csrfmiddlewaretoken": csrf},
    )
    print(f"  POST /molly/checkout/ -> {code} {url}")
    assert "/orders/MOL-" in url
    assert "צבע תווית" in body, "order confirm page should display label color snapshot"
    assert chosen_label.name in body, (
        f"order snapshot should preserve the chosen label color ({chosen_label.name})"
    )
    print(f"  OK: checkout created order with chosen label-color ({chosen_label.name}) snapshot at {url}")

    # 8. Order list
    code, url, body = fetch("/molly/orders/")
    print(f"  GET /molly/orders/ -> {code}")
    assert "MOL-" in body
    print("  OK: order list shows the new order")


def cleanup():
    from molly_catalog.models import MollyOrder, MollyCart
    section("3. Cleanup test data")
    # Delete orders & carts first because MollyOrder.user is PROTECT
    test_users = MollyCatalogUser.objects.filter(username="molly_test")
    MollyOrder.objects.filter(user__in=test_users).delete()
    MollyCart.objects.filter(user__in=test_users).delete()
    test_users.delete()
    MollyProduct.objects.filter(slug="blanket-classic").delete()
    MollyCategory.objects.filter(slug="blankets").delete()
    print("  cleaned up test orders, user, product, category")


if __name__ == "__main__":
    user, prod, cat, lc_black, lc_white = seed()
    try:
        http_flow(user, prod, cat, lc_black, lc_white)
    finally:
        cleanup()
    print("\nOK: all checks passed")
