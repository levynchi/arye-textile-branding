"""Rivhit Online API client for white catalog admin quotes (הצעת מחיר).

REST JSON against https://api.rivhit.co.il/online/RivhitOnlineAPI.svc, api_token in
every POST body. The token comes from ``settings.RIVHIT_API_TOKEN`` or the
``RIVHIT_API_TOKEN`` environment variable.
"""

import json
import os
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

BASE_URL = "https://api.rivhit.co.il/online/RivhitOnlineAPI.svc"
DEFAULT_TIMEOUT = 60
QUOTE_TYPE_NAME = "הצעת מחיר"
CACHE_TTL = 10 * 60


class RivhitApiError(Exception):
    """Error talking to Rivhit (including error_code from the server)."""

    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code


class RivhitOnlineClient:
    def __init__(self, api_token: str, timeout: int = DEFAULT_TIMEOUT):
        self.api_token = (api_token or "").strip()
        self.timeout = timeout
        if not self.api_token:
            raise RivhitApiError("לא הוגדר API TOKEN של ריווחית")

    def _request(self, method: str, payload: dict = None) -> dict:
        body = dict(payload or {})
        body["api_token"] = self.api_token
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/{method}",
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8")
                parsed = json.loads(detail)
            except (ValueError, AttributeError):
                raise RivhitApiError(f"שגיאת HTTP {e.code} מריווחית ({method})")
            message = parsed.get("client_message") or parsed.get("debug_message") or detail[:300]
            raise RivhitApiError(
                f"{message} (קוד {parsed.get('error_code', e.code)})",
                error_code=parsed.get("error_code", e.code),
            )
        except urllib.error.URLError as e:
            raise RivhitApiError(f"לא ניתן להתחבר לריווחית אונליין: {e.reason}")
        try:
            result = json.loads(raw)
        except ValueError:
            raise RivhitApiError(f"ריווחית החזירה תשובה לא צפויה (לא JSON) ב-{method}")
        error_code = result.get("error_code")
        if error_code not in (0, None):
            message = result.get("client_message") or result.get("debug_message") or f"שגיאה {error_code}"
            raise RivhitApiError(f"{message} (קוד {error_code})", error_code=error_code)
        return result.get("data") or {}

    def document_type_list(self) -> list:
        return self._request("Document.TypeList").get("document_type_list") or []

    def document_new(self, payload: dict) -> dict:
        return self._request("Document.New", payload)

    def customer_list(self) -> list:
        return self._request("Customer.List").get("customer_list") or []

    def item_list(self) -> list:
        return self._request("Item.List").get("item_list") or []


def rivhit_token() -> str:
    return (getattr(settings, "RIVHIT_API_TOKEN", "") or os.environ.get("RIVHIT_API_TOKEN", "")).strip()


def get_rivhit_client() -> RivhitOnlineClient:
    token = rivhit_token()
    if not token:
        raise RivhitApiError("לא הוגדר RIVHIT_API_TOKEN בהגדרות האתר (משתנה סביבה ב-Railway).")
    return RivhitOnlineClient(token)


def _type_name(entry: dict) -> str:
    return entry.get("document_name") or entry.get("name_document") or entry.get("document_type_name") or ""


def resolve_quote_document_type(client: RivhitOnlineClient) -> int:
    raw = (getattr(settings, "RIVHIT_QUOTE_DOCUMENT_TYPE", "") or os.environ.get("RIVHIT_QUOTE_DOCUMENT_TYPE", "")).strip()
    if raw:
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise RivhitApiError("RIVHIT_QUOTE_DOCUMENT_TYPE חייב להיות מספר")
    cached = cache.get("rivhit:quote_type")
    if cached:
        return cached
    for entry in client.document_type_list():
        if QUOTE_TYPE_NAME in _type_name(entry):
            doc_type = int(entry["document_type"])
            cache.set("rivhit:quote_type", doc_type, CACHE_TTL * 6)
            return doc_type
    raise RivhitApiError("לא נמצא סוג מסמך «הצעת מחיר» בריווחית. אפשר להגדיר RIVHIT_QUOTE_DOCUMENT_TYPE.")


def cached_customers(client: RivhitOnlineClient) -> list:
    customers = cache.get("rivhit:customers")
    if customers is None:
        customers = client.customer_list()
        cache.set("rivhit:customers", customers, CACHE_TTL)
    return customers


def cached_item_ids_by_barcode(client: RivhitOnlineClient) -> dict:
    mapping = cache.get("rivhit:items_by_barcode")
    if mapping is None:
        mapping = item_ids_by_barcode(client.item_list())
        cache.set("rivhit:items_by_barcode", mapping, CACHE_TTL)
    return mapping


def _digits(text) -> str:
    return "".join(ch for ch in str(text or "") if ch.isdigit())


def customer_name(entry: dict) -> str:
    return " ".join(part for part in (entry.get("last_name"), entry.get("first_name")) if part).strip()


def customer_display(entry: dict) -> str:
    bits = [customer_name(entry) or f"לקוח {entry.get('customer_id')}"]
    for key in ("city", "phone"):
        if entry.get(key):
            bits.append(str(entry[key]))
    return " · ".join(bits)


def match_customers(customers: list, phone: str = "", name: str = "") -> list:
    """Rivhit customers that look like this shop: same phone first, then all name words."""
    phone_digits = _digits(phone)
    if phone_digits.startswith("972"):
        phone_digits = "0" + phone_digits[3:]
    words = [w for w in str(name or "").replace("-", " ").split() if len(w) >= 2]
    by_phone, by_name = [], []
    for entry in customers:
        phones = {_digits(entry.get("phone")), _digits(entry.get("phone2"))}
        if len(phone_digits) >= 9 and phone_digits in phones:
            by_phone.append(entry)
            continue
        label = customer_name(entry)
        if words and all(w in label for w in words):
            by_name.append(entry)
    return by_phone + by_name


def item_ids_by_barcode(items: list) -> dict:
    """{barcode: item_id} from Rivhit's Item.List (barcode first, then catalog number)."""
    out = {}
    for entry in items:
        item_id = entry.get("item_id")
        if not item_id:
            continue
        for key in ("barcode", "item_part_num"):
            code = str(entry.get(key) or "").strip()
            if code and code not in out:
                out[code] = int(item_id)
    return out


def quote_line_description(item) -> str:
    """Rivhit line text for a WhiteOrderItem: product, colour/size, pack."""
    parts = [item.product_name]
    if item.color_name:
        parts.append(item.color_name)
        if item.size_name and item.size_name != item.color_name and not item.size_name.startswith(item.color_name):
            parts.append(item.size_name)
    elif item.size_name:
        parts.append(item.size_name)
    if item.pack_quantity > 1:
        parts.append(f"{item.pack_type_name} ({item.pack_quantity} יח')")
    return " | ".join(parts)[:100]


def create_quote_document(customer_id: int, order_number: str, items: list, client=None) -> dict:
    """Create a Rivhit quotation. items: [{description, quantity, price_nis, item_id?}, ...].

    ``item_id`` links the line to an existing Rivhit item (0 = free-text line). Quantities
    are packs and prices are per pack, excluding VAT — the same way the site prices them.
    """
    if not items:
        raise RivhitApiError("אין שורות להצעת מחיר")
    client = client or get_rivhit_client()
    document_type = resolve_quote_document_type(client)
    order_ref = (order_number or "").replace("ORD-", "", 1)[:15]
    payload = {
        "document_type": document_type,
        "customer_id": int(customer_id),
        "order": order_ref,
        "comments": f"הזמנה {order_number} מהאתר"[:400],
        "price_include_vat": False,
        "no_update_inventory": True,
        "items": [
            {
                "item_id": int(row.get("item_id") or 0),
                "quantity": float(row["quantity"]),
                "price_nis": float(row["price_nis"]),
                "price_mtc": 0,
                "description": (row["description"] or "")[:100],
            }
            for row in items
        ],
    }
    data = client.document_new(payload)
    data["document_type"] = data.get("document_type", document_type)
    return data
