from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AddRecipientsForm, CampaignForm, ContactForm, ContactNoteForm, TestEmailForm, parse_recipients
from .inbox import ensure_sync_thread, sync_enabled, sync_replies
from .models import Campaign, Contact, Recipient
from .services import send_test_email, start_campaign

DEFAULT_EMAIL_PATH = Path(__file__).parent / "templates" / "campaigns" / "default_email.html"


def default_html() -> str:
    # Read raw so curly braces in the email HTML are never parsed as template syntax
    return DEFAULT_EMAIL_PATH.read_text(encoding="utf-8")


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
    return render(request, "campaigns/campaign_form.html", {"form": form, "title": "קמפיין חדש"})


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
    return render(request, "campaigns/campaign_form.html", {"form": form, "title": f"עריכה: {campaign.name}", "campaign": campaign})


@staff_member_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return render(request, "campaigns/campaign_detail.html", {
        "campaign": campaign,
        "test_form": TestEmailForm(),
        "add_form": AddRecipientsForm(),
    })


@staff_member_required
def campaign_preview(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    html = (
        '<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        f"<body style=\"margin:0\">{campaign.html_content}</body></html>"
    )
    return HttpResponse(html)


@staff_member_required
@require_POST
def campaign_send_test(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    form = TestEmailForm(request.POST)
    if form.is_valid():
        try:
            send_test_email(campaign, form.cleaned_data["email"])
            messages.success(request, f"מייל בדיקה נשלח אל {form.cleaned_data['email']}.")
        except Exception as exc:  # noqa: BLE001 - show SMTP error to the user
            # #region agent log
            try:
                import json
                from pathlib import Path
                from django.utils import timezone as _tz
                Path(r"C:\My Web Sites\arye-textile-branding\debug-09228a.log").open("a", encoding="utf-8").write(json.dumps({"sessionId":"09228a","hypothesisId":"A,E,F","location":"campaigns/views.py:campaign_send_test","message":"test send failed","data":{"campaign_id":pk,"to_domain":(form.cleaned_data.get("email") or "").split("@")[-1],"exc_type":type(exc).__name__,"exc":str(exc)[:500]},"timestamp":int(_tz.now().timestamp()*1000)}, ensure_ascii=False)+"\n")
            except Exception:
                pass
            # #endregion
            messages.error(request, f"שליחת הבדיקה נכשלה: {exc}")
    else:
        messages.error(request, "כתובת מייל לא תקינה.")
    return redirect("campaign_detail", pk=pk)


@staff_member_required
@require_POST
def campaign_send(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    pending = campaign.pending_count
    # #region agent log
    try:
        import json
        from pathlib import Path
        from django.utils import timezone as _tz
        Path(r"C:\My Web Sites\arye-textile-branding\debug-09228a.log").open("a", encoding="utf-8").write(json.dumps({"sessionId":"09228a","hypothesisId":"C,F","location":"campaigns/views.py:campaign_send","message":"send all clicked","data":{"campaign_id":pk,"pending":pending,"status":campaign.status},"timestamp":int(_tz.now().timestamp()*1000)}, ensure_ascii=False)+"\n")
    except Exception:
        pass
    # #endregion
    if pending == 0:
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
