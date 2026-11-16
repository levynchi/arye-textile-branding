"""Send a white catalog order to the factory's order list (FactorySync + carton-lookup).

The desktop app and the phone page (levynchi.github.io/carton-lookup/orders.html)
share one file, ``orders.json`` in the ``levynchi/carton-lookup`` repo::

    {"updated": "2026-11-09 13:38:29", "customers": [...], "orders": [...]}

Both of them merge orders by ``id`` and keep the side with the newer ``updated_at``,
compared as plain "YYYY-MM-DD HH:MM:SS" strings in Israel local time. This module
writes a website order into that file through the GitHub Contents API, so it shows
up on the phone at once and in the desktop app on its next sync.

The token comes from ``settings.CARTON_LOOKUP_GITHUB_TOKEN`` or the
``CARTON_LOOKUP_GITHUB_TOKEN`` environment variable (Contents: read and write on
the carton-lookup repo).
"""

import base64
import json
import os
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

GITHUB_REPO = "levynchi/carton-lookup"
GITHUB_BRANCH = "main"
REMOTE_FILENAME = "orders.json"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{REMOTE_FILENAME}"
PAGE_URL = "https://levynchi.github.io/carton-lookup/orders.html"
DEFAULT_TIMEOUT = 20
MAX_ATTEMPTS = 3
ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

STATUS_OPEN = "פתוח"
STATUS_CLOSED = "סגור"
PACK_SINGLES = "יחידים"
PACKAGING_BY_QUANTITY = {3: "שלישיות", 5: "חמישיות", 1: PACK_SINGLES}
COLOR_FAN_VARIANT = "מניפת צבעים"
DEFAULT_COLOR = "לבן"

ACTION_CREATE = "create"
ACTION_REPLACE = "replace"
ACTION_BLOCKED = "blocked"

# Website product name -> the name the factory uses for the same garment.
# Anything not listed keeps its website name.
PRODUCT_NAMES = {
    "בגד גוף מעטפת": "בגד גוף מעטפת",
    "בגד גוף שרוול ארוך": "בגד גוף ש.א",
    "בגד גוף שרוול קצר": "בגד גוף ש.ק",
    "בגד גוף גופייה": "בגד גוף גופייה",
    "רגליות לתינוק": "רגליות",
    "מכנס פתוח (געטקס)": "גטקס",
}

# Website fabric name -> factory fabric name.
FABRIC_NAMES = {
    "טריקו ג'רזי": "טריקו",
}


class FactoryOrdersError(Exception):
    """Reading or writing the shared orders file failed."""


class FactoryOrdersConflict(FactoryOrdersError):
    """Someone else wrote orders.json between our read and our write."""


class FactoryOrderBlocked(FactoryOrdersError):
    """The order is already being packed, so the website must not overwrite it."""


def github_token() -> str:
    return (
        getattr(settings, "CARTON_LOOKUP_GITHUB_TOKEN", "")
        or os.environ.get("CARTON_LOOKUP_GITHUB_TOKEN", "")
    ).strip()


def now_str() -> str:
    return timezone.localtime(timezone.now(), ISRAEL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def order_page_url(order_id) -> str:
    return f"{PAGE_URL}?o={order_id}"


# --------------------------------------------------------------------------- conversion
def factory_product_name(site_name: str) -> str:
    name = (site_name or "").strip()
    return PRODUCT_NAMES.get(name, name)


def _is_color_line(item) -> bool:
    return bool((item.color_name or "").strip()) or (item.variant_name or "").strip() == COLOR_FAN_VARIANT


def _color_line_size(item) -> str:
    """Size of a colour-fan line. Its snapshot reads "colour · size", or just the colour."""
    color = (item.color_name or "").strip()
    size = (item.size_name or "").strip()
    if size == color:
        return ""
    prefix = f"{color} · "
    if color and size.startswith(prefix):
        return size[len(prefix):].strip()
    return size


def _variant_fabric(item) -> str:
    """Fabric of a size variant. Its snapshot name reads "<fabric> <size>"."""
    name = (item.variant_name or "").strip()
    size = (item.size_name or "").strip()
    if size and name.endswith(size):
        name = name[: -len(size)].strip()
    return FABRIC_NAMES.get(name, name)


def factory_line(item) -> dict:
    """One WhiteOrderItem as an orders.json line."""
    if _is_color_line(item):
        size = _color_line_size(item)
        fabric = ""
        color = (item.color_name or "").strip()
    else:
        size = (item.size_name or "").strip()
        fabric = _variant_fabric(item)
        color = DEFAULT_COLOR
    pack_quantity = int(item.pack_quantity or 1)
    quantity = int(item.quantity or 0)
    packaging = PACKAGING_BY_QUANTITY.get(pack_quantity)
    if packaging is None:
        # The factory only knows packs of 5, 3 and 1: any other pack is counted in units.
        packaging = PACK_SINGLES
        quantity *= pack_quantity
        pack_quantity = 1
    return {
        "product": factory_product_name(item.product_name),
        "size": size,
        "fabric_type": fabric,
        "fabric_color": color,
        "quantity": quantity,
        "packaging": packaging,
        "total_units": quantity * pack_quantity,
        "done": False,
        "sack": "",
    }


def preview_rows(order) -> list:
    """[{"item": WhiteOrderItem, "line": orders.json line}] for every line that has a quantity."""
    rows = []
    for item in sorted(order.items.all(), key=lambda i: i.pk):
        line = factory_line(item)
        if line["quantity"] > 0:
            rows.append({"item": item, "line": line})
    return rows


def order_notes(order) -> str:
    parts = [(order.notes or "").strip(), (order.admin_notes or "").strip()]
    return " | ".join(part for part in parts if part)


def _quote_entry(order):
    """The latest Rivhit quote made from this order, in the shape the factory apps read."""
    quote = order.quotes.order_by("-created").first()
    if quote is None or not quote.rivhit_document_number:
        return None
    number = quote.rivhit_document_number.strip()
    return {
        "document_type": quote.rivhit_document_type or 6,
        "document_number": int(number) if number.isdigit() else number,
        "document_link": quote.rivhit_document_link or "",
        "created_at": timezone.localtime(quote.created, ISRAEL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "price_include_vat": False,
    }


def build_factory_order(order, order_id: int, now: str = None) -> dict:
    """A WhiteOrder as an orders.json order with the given factory id."""
    now = now or now_str()
    lines = [row["line"] for row in preview_rows(order)]
    out = {
        "id": int(order_id),
        "order_number": order.order_number,
        "customer": (order.user.company_name or "").strip(),
        "date": timezone.localtime(order.created, ISRAEL_TZ).strftime("%Y-%m-%d"),
        "items": lines,
        "total_items": len(lines),
        "status": STATUS_OPEN,
        "notes": order_notes(order),
        "created_at": now,
        "updated_at": now,
    }
    quote = _quote_entry(order)
    if quote:
        out["rivhit_quote"] = quote
    return out


# --------------------------------------------------------------------------- the shared file
def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def find_existing(orders: list, order_number: str):
    """The entry already holding this website order, matched by its order number."""
    wanted = (order_number or "").strip()
    for entry in orders or []:
        if isinstance(entry, dict) and (entry.get("order_number") or "").strip() == wanted:
            return entry
    return None


def packing_started(entry: dict) -> bool:
    """True once the factory closed the order, ticked a line or put one in a sack."""
    if (entry.get("status") or "").strip() == STATUS_CLOSED:
        return True
    for line in entry.get("items") or []:
        if isinstance(line, dict) and (line.get("done") or str(line.get("sack") or "").strip()):
            return True
    return False


def next_order_id(orders: list) -> int:
    return max([_as_int(o.get("id")) for o in orders or [] if isinstance(o, dict)] + [0]) + 1


def plan_send(order, orders: list):
    """What sending would do: (ACTION_CREATE | ACTION_REPLACE | ACTION_BLOCKED, existing entry or None)."""
    existing = find_existing(orders, order.order_number)
    if existing is None:
        return ACTION_CREATE, None
    if packing_started(existing):
        return ACTION_BLOCKED, existing
    return ACTION_REPLACE, existing


def apply_order(order, data: dict, now: str = None):
    """Put the order into the parsed orders.json content. Returns (action, entry).

    A new order is appended under the next free id. An order that is already there
    and untouched by the factory gets the website's current lines; one that is being
    packed raises FactoryOrderBlocked so no tick or sack number is lost.
    """
    orders = [o for o in (data.get("orders") or []) if isinstance(o, dict)]
    action, existing = plan_send(order, orders)
    if action == ACTION_BLOCKED:
        raise FactoryOrderBlocked(
            f"ההזמנה {order.order_number} כבר בהכנה בהזמנות (יש שורות מסומנות, שקים, או שהיא נסגרה). "
            "כדי לא למחוק את הסימונים, שינויים עושים ישירות בדף ההזמנות."
        )
    now = now or now_str()
    if existing is None:
        entry = build_factory_order(order, next_order_id(orders), now)
        orders.append(entry)
    else:
        entry = build_factory_order(order, _as_int(existing.get("id")), now)
        entry["created_at"] = existing.get("created_at") or now
        if not entry["notes"]:
            entry["notes"] = (existing.get("notes") or "").strip()
        if "rivhit_quote" not in entry and existing.get("rivhit_quote"):
            entry["rivhit_quote"] = existing["rivhit_quote"]
        orders = [entry if o is existing else o for o in orders]
    data["orders"] = sorted(orders, key=lambda o: _as_int(o.get("id")))
    data.setdefault("customers", [])
    data["updated"] = now
    return action, entry


# --------------------------------------------------------------------------- GitHub
def _headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
        "User-Agent": "arye-textil-white-catalog",
    }


def _http_error(error, doing: str) -> FactoryOrdersError:
    try:
        detail = str(json.loads(error.read().decode("utf-8")).get("message") or "")
    except Exception:
        detail = ""
    if error.code in (401, 403):
        hint = "טוקן GitHub שגוי, פג תוקף, או בלי הרשאת כתיבה לרפו carton-lookup"
    elif error.code == 404:
        hint = "הרפו לא נמצא, או שלטוקן אין הרשאת כתיבה לרפו carton-lookup"
    else:
        hint = "שגיאה מ-GitHub"
    return FactoryOrdersError(f"{hint} ({doing}, קוד {error.code}{': ' + detail if detail else ''})")


def fetch_orders_file(token: str = None, timeout: int = DEFAULT_TIMEOUT):
    """Read orders.json. Returns (data dict, blob sha or None when the file does not exist yet)."""
    token = token or github_token()
    if not token:
        raise FactoryOrdersError("לא הוגדר CARTON_LOOKUP_GITHUB_TOKEN בהגדרות האתר (משתנה סביבה ב-Railway).")
    url = f"{API_URL}?ref={GITHUB_BRANCH}&t={int(time.time())}"
    req = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # No orders.json yet: the first write creates it.
            return {"orders": [], "customers": []}, None
        raise _http_error(e, "קריאת ההזמנות")
    except urllib.error.URLError as e:
        raise FactoryOrdersError(f"לא ניתן להתחבר ל-GitHub: {e.reason}")
    except ValueError:
        raise FactoryOrdersError("GitHub החזיר תשובה לא צפויה בקריאת ההזמנות")
    try:
        raw = base64.b64decode(body.get("content") or "").decode("utf-8")
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        # Never overwrite a file we could not read: that would wipe every order in it.
        raise FactoryOrdersError("הקובץ orders.json ברפו אינו JSON תקין. לא נשלח דבר.")
    if isinstance(data, list):
        data = {"orders": data}
    if not isinstance(data, dict):
        raise FactoryOrdersError("הקובץ orders.json ברפו במבנה לא צפוי. לא נשלח דבר.")
    return data, body.get("sha")


def put_orders_file(data: dict, sha, message: str, token: str = None, timeout: int = DEFAULT_TIMEOUT):
    """Write orders.json. Raises FactoryOrdersConflict when the file changed since it was read."""
    token = token or github_token()
    content = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
    body = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha
    headers = _headers(token)
    headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (409, 422):
            raise FactoryOrdersConflict("הקובץ השתנה בזמן השליחה")
        raise _http_error(e, "כתיבת ההזמנות")
    except urllib.error.URLError as e:
        raise FactoryOrdersError(f"לא ניתן להתחבר ל-GitHub: {e.reason}")


def send_order(order) -> dict:
    """Write the order into the shared orders file.

    Returns {"action": ACTION_CREATE | ACTION_REPLACE, "id": factory order id, "url": phone page link}.
    Raises FactoryOrdersError (FactoryOrderBlocked when the factory already started packing it).
    """
    token = github_token()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        data, sha = fetch_orders_file(token)
        action, entry = apply_order(order, data)
        verb = "Add" if action == ACTION_CREATE else "Update"
        try:
            put_orders_file(data, sha, f"{verb} order {entry['id']} ({order.order_number}) from website", token)
        except FactoryOrdersConflict:
            if attempt == MAX_ATTEMPTS:
                raise FactoryOrdersError("ההזמנות התעדכנו ממקום אחר בזמן השליחה. נסו שוב בעוד רגע.")
            continue
        return {"action": action, "id": entry["id"], "url": order_page_url(entry["id"])}
