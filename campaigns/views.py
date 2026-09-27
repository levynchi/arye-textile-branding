from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from .forms import AddRecipientsForm, CampaignForm, ContactForm, ContactNoteForm, TestEmailForm, parse_recipients
from .inbox import ensure_sync_thread, sync_enabled, sync_replies
from .models import Campaign, Contact, Recipient
from .services import send_test_email, start_campaign

TEMPLATES_DIR = Path(__file__).parent / "templates" / "campaigns"

# Built-in designed emails available in the "מאגר מיילים" picker. First one is the default
# for new campaigns. (key, label, file name)
EMAIL_TEMPLATES = [
    ("winter_2026", "חורף 2026 — העיצוב החדש", "winter_email.html"),
    ("welcome", "מייל WELCOME — העיצוב הקודם", "default_email.html"),
]
DEFAULT_TEMPLATE_KEY = EMAIL_TEMPLATES[0][0]
DEFAULT_EMAIL_PATH = TEMPLATES_DIR / EMAIL_TEMPLATES[0][2]


def default_html() -> str:
    # Read raw so curly braces in the email HTML are never parsed as template syntax
    return DEFAULT_EMAIL_PATH.read_text(encoding="utf-8")


def library_items(exclude_pk=None):
    """Everything the admin can pick from: built-in templates + HTML of previous campaigns."""
    templates = [{"key": f"tpl:{key}", "label": label} for key, label, _ in EMAIL_TEMPLATES]
    campaigns = Campaign.objects.exclude(pk=exclude_pk) if exclude_pk else Campaign.objects.all()
    previous = [
        {"key": f"campaign:{c.pk}", "label": f"{c.name} — {c.created_at:%d/%m/%Y}"}
        for c in campaigns.only("pk", "name", "created_at")
    ]
    return templates, previous


def library_lookup(key: str):
    """Resolve a picker key to (label, html). Raises Http404 for unknown keys."""
    kind, _, ident = key.partition(":")
    if kind == "tpl":
        for tpl_key, label, filename in EMAIL_TEMPLATES:
            if tpl_key == ident:
                return label, (TEMPLATES_DIR / filename).read_text(encoding="utf-8")
        raise Http404
    if kind == "campaign" and ident.isdigit():
        campaign = get_object_or_404(Campaign, pk=int(ident))
        return campaign.name, campaign.html_content
    raise Http404


def _wrap_preview(html: str) -> HttpResponse:
    if "<html" in html.lower():
        return HttpResponse(html)
    return HttpResponse(
        '<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        f"<body style=\"margin:0\">{html}</body></html>"
    )


def add_recipients_with_dedup(campaign, raw, include_repeats):
    """Add pasted recipients to a campaign, skipping past contacts unless asked otherwise.

    Returns (added_count, skipped_repeats, blocked_emails) where skipped_repeats is a
    list of (email, previous_recipient) and blocked_emails are 'not interested' contacts.
    """
    added = 0
    skipped_repeats = []
    blocked = []
    for email, name in parse_recipients(raw):
        contact = Contact.get_or_create_for(email, name)
        if contact.status == Contact.Status.NOT_INTERESTED:
            blocked.append(email)
            continue
        if not include_repeats:
            previous = (
                Recipient.objects.filter(email=email, status=Recipient.Status.SENT)
                .exclude(campaign=campaign)
                .select_related("campaign")
                .order_by("-sent_at")
                .first()
            )
            if previous is not None:
                skipped_repeats.append((email, previous))
                continue
        _, created = Recipient.objects.get_or_create(
            campaign=campaign, email=email, defaults={"name": name, "contact": contact},
        )
        added += int(created)
    return added, skipped_repeats, blocked


def _report_dedup(request, added, skipped_repeats, blocked):
    if added:
        messages.success(request, f"נוספו {added} נמענים.")
    for email, previous in skipped_repeats:
        sent_date = previous.sent_at.strftime("%d/%m/%Y") if previous.sent_at else ""
        messages.warning(
            request,
            f"{email} דולג — כבר נשלח אליו מייל בקמפיין \"{previous.campaign.name}\" בתאריך {sent_date}. "
            "כדי לכלול בכל זאת, סמנו את התיבה והדביקו שוב.",
        )
    for email in blocked:
        messages.error(request, f"{email} לא נוסף — הלקוח מסומן \"לא מעוניין\".")


@staff_member_required
def campaign_list(request):
    ensure_sync_thread()
    return render(request, "campaigns/campaign_list.html", {"campaigns": Campaign.objects.all()})


@staff_member_required
def campaign_create(request):
    if request.method == "POST":
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            added, skipped, blocked = add_recipients_with_dedup(
                campaign, form.cleaned_data["recipients_raw"], form.cleaned_data["include_repeats"],
            )
            messages.success(request, f"הקמפיין נוצר עם {campaign.total_count} נמענים.")
            _report_dedup(request, 0, skipped, blocked)
            return redirect("campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm(initial={"html_content": default_html()})
    templates, previous = library_items()
    return render(request, "campaigns/campaign_form.html", {
        "form": form, "title": "קמפיין חדש",
        "library_templates": templates, "library_previous": previous,
        "library_selected": f"tpl:{DEFAULT_TEMPLATE_KEY}",
    })


@staff_member_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == "POST":
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            added, skipped, blocked = add_recipients_with_dedup(
                campaign, form.cleaned_data["recipients_raw"], form.cleaned_data["include_repeats"],
            )
            messages.success(request, "הקמפיין עודכן.")
            _report_dedup(request, added, skipped, blocked)
            return redirect("campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign)
    templates, previous = library_items(exclude_pk=campaign.pk)
    return render(request, "campaigns/campaign_form.html", {
        "form": form, "title": f"עריכה: {campaign.name}", "campaign": campaign,
        "library_templates": templates, "library_previous": previous,
        "library_selected": "",
    })


@staff_member_required
def library_html(request, key):
    label, html = library_lookup(key)
    return JsonResponse({"key": key, "label": label, "html": html})


@staff_member_required
@xframe_options_sameorigin
def library_preview(request, key):
    _, html = library_lookup(key)
    return _wrap_preview(html)


@staff_member_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return render(request, "campaigns/campaign_detail.html", {
        "campaign": campaign,
        "test_form": TestEmailForm(),
        "add_form": AddRecipientsForm(),
    })


@staff_member_required
@xframe_options_sameorigin
def campaign_preview(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return _wrap_preview(campaign.html_content)


@staff_member_required
@require_POST
def campaign_send_test(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = TestEmailForm(request.POST)
    if form.is_valid():
        try:
            send_test_email(campaign, form.cleaned_data["email"])
            messages.success(request, f"מייל בדיקה נשלח אל {form.cleaned_data['email']}.")
        except Exception as exc:  # noqa: BLE001 - show send error to the user
            messages.error(request, f"שליחת הבדיקה נכשלה: {exc}")
    else:
        messages.error(request, "כתובת מייל לא תקינה.")
    return redirect("campaign_detail", pk=pk)


@staff_member_required
@require_POST
def campaign_send(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if campaign.queued_count == 0:
        messages.warning(request, "אין נמענים ממתינים לשליחה.")
    elif start_campaign(campaign):
        messages.success(request, "השליחה התחילה! העמוד מתעדכן אוטומטית.")
    else:
        messages.warning(request, "הקמפיין כבר בשליחה.")
    return redirect("campaign_detail", pk=pk)


@staff_member_required
@require_POST
def campaign_add_recipients(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = AddRecipientsForm(request.POST)
    if form.is_valid():
        added, skipped, blocked = add_recipients_with_dedup(
            campaign, form.cleaned_data["recipients_raw"], form.cleaned_data["include_repeats"],
        )
        _report_dedup(request, added, skipped, blocked)
    return redirect("campaign_detail", pk=pk)


@staff_member_required
def campaign_status(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return JsonResponse({
        "status": campaign.status,
        "total": campaign.total_count,
        "sent": campaign.sent_count,
        "failed": campaign.failed_count,
        "pending": campaign.pending_count,
        "recipients": [
            {
                "email": r.email, "name": r.name, "status": r.status, "error": r.error,
                "repeat": r.is_repeat, "contact_id": r.contact_id,
            }
            for r in campaign.recipients.select_related("contact")
        ],
    })


@staff_member_required
@require_POST
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.delete()
    messages.success(request, "הקמפיין נמחק.")
    return redirect("campaign_list")


# --- Contacts (customer cards) ---

@staff_member_required
def contact_list(request):
    ensure_sync_thread()
    contacts = Contact.objects.all()
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        contacts = contacts.filter(Q(email__icontains=query) | Q(name__icontains=query))
    if status:
        contacts = contacts.filter(status=status)
    return render(request, "campaigns/contact_list.html", {
        "contacts": contacts,
        "query": query,
        "status": status,
        "statuses": Contact.Status.choices,
        "sync_enabled": sync_enabled(),
    })


@staff_member_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    return render(request, "campaigns/contact_detail.html", {
        "contact": contact,
        "form": ContactForm(instance=contact),
        "note_form": ContactNoteForm(),
        "recipients": contact.recipients.select_related("campaign").order_by("-id"),
        "replies": contact.replies.select_related("recipient__campaign"),
        "notes": contact.contact_notes.all(),
    })


@staff_member_required
@require_POST
def contact_update(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = ContactForm(request.POST, instance=contact)
    if form.is_valid():
        form.save()
        messages.success(request, "כרטיס הלקוח עודכן.")
    else:
        messages.error(request, "לא ניתן לעדכן — בדקו את הנתונים.")
    return redirect("contact_detail", pk=pk)


@staff_member_required
@require_POST
def contact_add_note(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = ContactNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.contact = contact
        note.save()
        messages.success(request, "ההערה נוספה ליומן.")
    return redirect("contact_detail", pk=pk)


@staff_member_required
@require_POST
def replies_sync(request):
    if not sync_enabled():
        messages.warning(request, "סנכרון תגובות דורש חיבור Gmail (GMAIL_USER + GMAIL_APP_PASSWORD).")
    else:
        try:
            count = sync_replies()
            if count:
                messages.success(request, f"נקלטו {count} תגובות חדשות.")
            else:
                messages.success(request, "הסנכרון הסתיים — אין תגובות חדשות.")
        except Exception as exc:  # noqa: BLE001 - show IMAP error to the user
            messages.error(request, f"הסנכרון נכשל: {exc}")
    return redirect(request.POST.get("next") or "contact_list")
