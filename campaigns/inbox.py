"""Pull reply emails from the Gmail inbox (IMAP) and attach them to contacts.

Matching logic, in order of accuracy:
1. In-Reply-To / References header matches a Message-ID we stored at send time
   -> reply is linked to the exact campaign recipient.
2. Sender address matches an existing Contact -> linked to the contact only.
Anything else in the inbox is ignored.
"""
import email
import imaplib
import logging
import threading
import time
from datetime import timedelta
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime

from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Contact, Recipient, Reply

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
SEARCH_DAYS_BACK = 30
SYNC_INTERVAL_SECONDS = 300
MAX_BODY_CHARS = 10000


def sync_enabled() -> bool:
    return bool(getattr(settings, "EMAIL_HOST_USER", "") and getattr(settings, "EMAIL_HOST_PASSWORD", ""))


def _decode_subject(msg: Message) -> str:
    try:
        return str(make_header(decode_header(msg.get("Subject", ""))))
    except Exception:  # noqa: BLE001 - malformed headers shouldn't kill the sync
        return msg.get("Subject", "")


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            if part.get_content_type() == "text/plain" and "attachment" not in disposition:
                return _decode_part(part)
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return strip_tags(_decode_part(part))
        return ""
    if msg.get_content_type() == "text/html":
        return strip_tags(_decode_part(msg))
    return _decode_part(msg)


def _referenced_ids(msg: Message) -> list[str]:
    refs = f"{msg.get('In-Reply-To', '')} {msg.get('References', '')}"
    return [r for r in refs.split() if r.startswith("<")]


def _received_at(msg: Message):
    try:
        dt = parsedate_to_datetime(msg.get("Date", ""))
        if dt.tzinfo is None:
            dt = timezone.make_aware(dt)
        return dt
    except Exception:  # noqa: BLE001
        return timezone.now()


def process_incoming_message(msg: Message) -> Reply | None:
    """Save one parsed inbox email as a Reply if it belongs to a known contact.

    Returns the created Reply, or None if the email is irrelevant or already stored.
    """
    message_id = (msg.get("Message-ID") or "").strip()
    from_email = parseaddr(msg.get("From", ""))[1].lower()
    if not message_id or not from_email:
        return None
    if from_email == (getattr(settings, "EMAIL_HOST_USER", "") or "").lower():
        return None
    if Reply.objects.filter(message_id=message_id).exists():
        return None

    recipient = None
    refs = _referenced_ids(msg)
    if refs:
        recipient = Recipient.objects.filter(message_id__in=refs).select_related("contact").first()

    if recipient is not None:
        contact = recipient.contact or Contact.get_or_create_for(recipient.email, recipient.name)
    else:
        contact = Contact.objects.filter(email=from_email).first()
        if contact is None:
            return None

    reply = Reply.objects.create(
        contact=contact,
        recipient=recipient,
        from_email=from_email,
        subject=_decode_subject(msg)[:500],
        body=_extract_body(msg).strip()[:MAX_BODY_CHARS],
        message_id=message_id,
        received_at=_received_at(msg),
    )

    if contact.status in (Contact.Status.NEW, Contact.Status.CONTACTED):
        contact.status = Contact.Status.REPLIED
        contact.save(update_fields=["status", "updated_at"])
    return reply


def sync_replies() -> int:
    """Scan the Gmail inbox and store new replies. Returns how many were saved."""
    if not sync_enabled():
        return 0

    since = (timezone.now() - timedelta(days=SEARCH_DAYS_BACK)).strftime("%d-%b-%Y")
    own_email = (getattr(settings, "EMAIL_HOST_USER", "") or "").lower()
    new_replies = 0

    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        imap.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)  # gated by sync_enabled()
        imap.select("INBOX", readonly=True)
        _, data = imap.search(None, f'(SINCE "{since}")')
        for num in data[0].split():
            # Cheap header-only fetch first; full body only for relevant emails
            _, hdr_data = imap.fetch(num, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM)])")
            headers = email.message_from_bytes(hdr_data[0][1])
            message_id = (headers.get("Message-ID") or "").strip()
            from_email = parseaddr(headers.get("From", ""))[1].lower()
            if not message_id or not from_email or from_email == own_email:
                continue
            if Reply.objects.filter(message_id=message_id).exists():
                continue

            _, msg_data = imap.fetch(num, "(BODY.PEEK[])")
            parsed = email.message_from_bytes(msg_data[0][1])
            try:
                if process_incoming_message(parsed) is not None:
                    new_replies += 1
            except Exception:  # noqa: BLE001 - one bad email must not stop the scan
                logger.exception("Failed processing inbox message %s", message_id)
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass

    if new_replies:
        logger.info("Inbox sync: saved %d new replies", new_replies)
    return new_replies


_sync_thread_lock = threading.Lock()
_sync_thread_started = False


def ensure_sync_thread():
    """Start the periodic inbox sync thread once per process (no-op afterwards)."""
    global _sync_thread_started
    if _sync_thread_started or not sync_enabled():
        return
    with _sync_thread_lock:
        if _sync_thread_started:
            return
        _sync_thread_started = True
        thread = threading.Thread(target=_sync_loop, daemon=True, name="inbox-sync")
        thread.start()


def _sync_loop():
    while True:
        try:
            sync_replies()
        except Exception:  # noqa: BLE001 - keep the loop alive through IMAP hiccups
            logger.exception("Inbox sync failed")
        time.sleep(SYNC_INTERVAL_SECONDS)
