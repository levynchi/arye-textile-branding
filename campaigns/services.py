"""Campaign sending logic - runs in a background thread, one email at a time."""
import logging
import random
import threading
import time
from email.utils import make_msgid

import resend
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Campaign, Contact, Recipient

logger = logging.getLogger(__name__)

RESEND_FROM_ADDRESS = "onboarding@resend.dev"

# Delay between emails so the sender is not flagged as a bulk sender
MIN_DELAY_SECONDS = 3
MAX_DELAY_SECONDS = 7


def personalize(text: str, recipient: Recipient) -> str:
    name = recipient.name or "לקוחות יקרים"
    return text.replace("{{name}}", name).replace("{{שם}}", name)


def campaign_from_header(campaign: Campaign) -> str:
    display = (campaign.from_name or "Arye Textile").strip()
    return f"{display} <{RESEND_FROM_ADDRESS}>"


def send_via_resend(campaign: Campaign, to_email: str, recipient: Recipient | None = None) -> str:
    """Send one campaign email through Resend. Returns the Message-ID we assigned."""
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not configured")

    html = campaign.html_content
    subject = campaign.subject
    if recipient is not None:
        html = personalize(html, recipient)
        subject = personalize(subject, recipient)

    message_id = make_msgid(domain="resend.dev")
    resend.api_key = settings.RESEND_API_KEY
    payload = {
        "from": campaign_from_header(campaign),
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": strip_tags(html),
        "reply_to": settings.CONTACT_EMAIL,
        "headers": {"Message-ID": message_id},
    }
    resend.Emails.send(payload)
    return message_id


def send_test_email(campaign: Campaign, to_email: str):
    """Send a single test email synchronously. Raises on failure."""
    send_via_resend(campaign, to_email)


def _mark_contact_contacted(recipient: Recipient):
    """Update the contact card after a successful send."""
    contact = recipient.contact or Contact.get_or_create_for(recipient.email, recipient.name)
    recipient.contact = contact
    contact.last_contacted_at = recipient.sent_at
    if contact.status == Contact.Status.NEW:
        contact.status = Contact.Status.CONTACTED
    contact.save(update_fields=["last_contacted_at", "status", "updated_at"])


def _run_campaign(campaign_id: int):
    campaign = Campaign.objects.get(pk=campaign_id)
    pending = campaign.recipients.filter(status=Recipient.Status.PENDING).select_related("contact")

    for recipient in pending:
        if recipient.contact and recipient.contact.status == Contact.Status.NOT_INTERESTED:
            recipient.status = Recipient.Status.FAILED
            recipient.error = 'לא נשלח — הלקוח מסומן "לא מעוניין"'
            recipient.save()
            continue
        try:
            message_id = send_via_resend(campaign, recipient.email, recipient)
            recipient.status = Recipient.Status.SENT
            recipient.sent_at = timezone.now()
            recipient.message_id = message_id
            recipient.error = ""
            _mark_contact_contacted(recipient)
        except Exception as exc:  # noqa: BLE001 - record any send failure per recipient
            logger.exception("Failed sending to %s", recipient.email)
            recipient.status = Recipient.Status.FAILED
            recipient.error = str(exc)[:2000]
        recipient.save()
        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    campaign.status = Campaign.Status.DONE
    campaign.save(update_fields=["status", "updated_at"])


def start_campaign(campaign: Campaign) -> bool:
    """Kick off sending in a background thread. Returns False if already sending."""
    if campaign.status == Campaign.Status.SENDING:
        return False
    campaign.status = Campaign.Status.SENDING
    campaign.save(update_fields=["status", "updated_at"])
    thread = threading.Thread(target=_run_campaign, args=(campaign.pk,), daemon=True)
    thread.start()
    return True
