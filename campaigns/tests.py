"""End-to-end tests: campaign send -> contact cards -> incoming reply -> dedup."""
from email.message import EmailMessage
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .inbox import process_incoming_message
from .models import Campaign, Contact, Recipient, Reply
from .services import _run_campaign
from .views import add_recipients_with_dedup


def make_campaign(name="קמפיין בדיקה", **kwargs):
    return Campaign.objects.create(
        name=name, subject="שלום {{שם}}", html_content="<p>שלום {{שם}}</p>", **kwargs,
    )


def build_reply(from_email, in_reply_to=None, subject="RE: שלום", body="מעוניינים בקטלוג!", message_id="<reply-1@shop.com>"):
    msg = EmailMessage()
    msg["Message-ID"] = message_id
    msg["From"] = f"חנות <{from_email}>"
    msg["Subject"] = subject
    msg["Date"] = "Mon, 27 Jul 2026 10:00:00 +0300"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    msg.set_content(body)
    return msg


@override_settings(
    RESEND_API_KEY="test-key",
    CONTACT_EMAIL="levynchi@gmail.com",
    RESEND_FROM_EMAIL="info@arye-boutique.co.il",
)
class CampaignFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("admin", password="pass", is_staff=True)
        self.client.force_login(self.user)
        self.resend_patch = patch("campaigns.services.resend.Emails.send", return_value={"id": "msg_test"})
        self.mock_send = self.resend_patch.start()
        self.addCleanup(self.resend_patch.stop)

    @patch("campaigns.services.time.sleep", lambda *_: None)
    def run_campaign_sync(self, campaign):
        _run_campaign(campaign.pk)

    def test_anonymous_is_redirected_to_admin_login(self):
        self.client.logout()
        response = self.client.get(reverse("campaign_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_non_staff_is_redirected(self):
        regular = User.objects.create_user("shop", password="pass")
        self.client.force_login(regular)
        response = self.client.get(reverse("campaign_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_send_creates_contacts_and_saves_message_id(self):
        campaign = make_campaign()
        add_recipients_with_dedup(campaign, "shop1@test.com, חנות אחת\nshop2@test.com", include_repeats=False)
        self.assertEqual(campaign.recipients.count(), 2)
        self.assertEqual(Contact.objects.count(), 2)

        self.run_campaign_sync(campaign)
        self.assertEqual(self.mock_send.call_count, 2)

        recipient = campaign.recipients.get(email="shop1@test.com")
        self.assertEqual(recipient.status, Recipient.Status.SENT)
        self.assertTrue(recipient.message_id.startswith("<"))
        self.assertEqual(recipient.contact.status, Contact.Status.CONTACTED)
        self.assertIsNotNone(recipient.contact.last_contacted_at)

        first_payload = self.mock_send.call_args_list[0].args[0]
        self.assertEqual(first_payload["from"], "Arye Textile <info@arye-boutique.co.il>")
        self.assertEqual(first_payload["reply_to"], "levynchi@gmail.com")

    def test_reply_matched_by_message_id(self):
        campaign = make_campaign()
        add_recipients_with_dedup(campaign, "shop1@test.com, חנות אחת", include_repeats=False)
        self.run_campaign_sync(campaign)
        recipient = campaign.recipients.get()

        reply = process_incoming_message(build_reply("shop1@test.com", in_reply_to=recipient.message_id))
        self.assertIsNotNone(reply)
        self.assertEqual(reply.recipient, recipient)
        self.assertEqual(reply.campaign, campaign)
        self.assertEqual(reply.contact.status, Contact.Status.REPLIED)
        self.assertIn("מעוניינים", reply.body)

        # Same message again is ignored (dedupe by Message-ID)
        self.assertIsNone(process_incoming_message(build_reply("shop1@test.com", in_reply_to=recipient.message_id)))
        self.assertEqual(Reply.objects.count(), 1)

    def test_reply_matched_by_sender_address_only(self):
        contact = Contact.objects.create(email="shop9@test.com", name="חנות תשע", status=Contact.Status.CONTACTED)
        reply = process_incoming_message(build_reply("shop9@test.com", message_id="<no-refs@shop.com>"))
        self.assertIsNotNone(reply)
        self.assertIsNone(reply.recipient)
        self.assertEqual(reply.contact, contact)
        contact.refresh_from_db()
        self.assertEqual(contact.status, Contact.Status.REPLIED)

    def test_reply_from_unknown_sender_is_ignored(self):
        self.assertIsNone(process_incoming_message(build_reply("stranger@test.com", message_id="<x@y.com>")))
        self.assertEqual(Reply.objects.count(), 0)

    def test_reply_does_not_downgrade_customer_status(self):
        Contact.objects.create(email="vip@test.com", status=Contact.Status.CUSTOMER)
        process_incoming_message(build_reply("vip@test.com", message_id="<vip@y.com>"))
        self.assertEqual(Contact.objects.get(email="vip@test.com").status, Contact.Status.CUSTOMER)

    def test_dedup_skips_previously_sent(self):
        old = make_campaign("קמפיין ישן")
        add_recipients_with_dedup(old, "shop1@test.com", include_repeats=False)
        self.run_campaign_sync(old)

        new = make_campaign("קמפיין חדש")
        added, skipped, blocked = add_recipients_with_dedup(
            new, "shop1@test.com\nfresh@test.com", include_repeats=False,
        )
        self.assertEqual(added, 1)
        self.assertEqual([email for email, _ in skipped], ["shop1@test.com"])
        self.assertEqual(blocked, [])
        self.assertFalse(new.recipients.filter(email="shop1@test.com").exists())

        # With the checkbox on, the repeat is included and marked as such
        added, skipped, _ = add_recipients_with_dedup(new, "shop1@test.com", include_repeats=True)
        self.assertEqual(added, 1)
        self.assertEqual(skipped, [])
        self.assertTrue(new.recipients.get(email="shop1@test.com").is_repeat)

    def test_not_interested_blocked_from_adding_and_sending(self):
        Contact.objects.create(email="no@test.com", status=Contact.Status.NOT_INTERESTED)
        campaign = make_campaign()
        added, skipped, blocked = add_recipients_with_dedup(campaign, "no@test.com", include_repeats=True)
        self.assertEqual((added, blocked), (0, ["no@test.com"]))

        # Even a recipient added before being marked 'not interested' is not sent
        other = make_campaign("קמפיין נוסף")
        added, _, _ = add_recipients_with_dedup(other, "later@test.com", include_repeats=False)
        self.assertEqual(added, 1)
        Contact.objects.filter(email="later@test.com").update(status=Contact.Status.NOT_INTERESTED)
        self.run_campaign_sync(other)
        recipient = other.recipients.get()
        self.assertEqual(recipient.status, Recipient.Status.FAILED)
        self.assertEqual(self.mock_send.call_count, 0)

    def test_contact_pages_and_notes(self):
        contact = Contact.objects.create(email="shop1@test.com", name="חנות אחת")
        response = self.client.get(reverse("contact_list"), {"q": "חנות"})
        self.assertContains(response, "shop1@test.com")
        self.assertNotContains(response, "סנכרון תגובות מ-Gmail")

        response = self.client.get(reverse("contact_detail", args=[contact.pk]))
        self.assertContains(response, "יומן פעילות")

        self.client.post(reverse("contact_add_note", args=[contact.pk]), {"text": "לחזור אליו בעוד שבוע"})
        self.assertEqual(contact.contact_notes.count(), 1)

        self.client.post(reverse("contact_update", args=[contact.pk]), {
            "name": "חנות אחת", "status": Contact.Status.IN_TALKS, "notes": "מנהל נחמד",
        })
        contact.refresh_from_db()
        self.assertEqual(contact.status, Contact.Status.IN_TALKS)

    def test_status_json_includes_repeat_and_contact(self):
        campaign = make_campaign()
        add_recipients_with_dedup(campaign, "shop1@test.com", include_repeats=False)
        data = self.client.get(reverse("campaign_status", args=[campaign.pk])).json()
        recipient = data["recipients"][0]
        self.assertIn("repeat", recipient)
        self.assertIsNotNone(recipient["contact_id"])

    def test_send_view_runs_inline_and_marks_sent(self):
        campaign = make_campaign()
        add_recipients_with_dedup(campaign, "shop1@test.com", include_repeats=False)
        with patch("campaigns.services.time.sleep", lambda *_: None):
            response = self.client.post(reverse("campaign_send", args=[campaign.pk]))
        self.assertEqual(response.status_code, 302)
        recipient = campaign.recipients.get()
        self.assertEqual(recipient.status, Recipient.Status.SENT)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.DONE)

    def test_send_retries_if_stuck_sending_with_pending(self):
        campaign = make_campaign()
        add_recipients_with_dedup(campaign, "shop1@test.com", include_repeats=False)
        campaign.status = Campaign.Status.SENDING
        campaign.save(update_fields=["status", "updated_at"])
        with patch("campaigns.services.time.sleep", lambda *_: None):
            self.client.post(reverse("campaign_send", args=[campaign.pk]))
        self.assertEqual(campaign.recipients.get().status, Recipient.Status.SENT)

    def test_send_retries_failed_recipient(self):
        campaign = make_campaign()
        add_recipients_with_dedup(campaign, "shop1@test.com", include_repeats=False)
        recipient = campaign.recipients.get()
        recipient.status = Recipient.Status.FAILED
        recipient.error = "You can only send testing emails to your own email address"
        recipient.save()
        with patch("campaigns.services.time.sleep", lambda *_: None):
            self.client.post(reverse("campaign_send", args=[campaign.pk]))
        recipient.refresh_from_db()
        self.assertEqual(recipient.status, Recipient.Status.SENT)
        self.assertEqual(recipient.error, "")

    def test_new_campaign_form_lists_library_and_defaults_to_winter(self):
        old = make_campaign("קמפיין ישן")
        response = self.client.get(reverse("campaign_create"))
        self.assertContains(response, "מאגר מיילים")
        self.assertContains(response, 'value="tpl:winter_2026" selected')
        self.assertContains(response, 'value="tpl:welcome"')
        self.assertContains(response, f'value="campaign:{old.pk}"')
        self.assertContains(response, "emails/winter2026/hero_bg.jpg")  # default html_content

    def test_library_html_and_preview(self):
        old = make_campaign("קמפיין ישן")
        data = self.client.get(reverse("library_html", args=["tpl:winter_2026"])).json()
        self.assertEqual(data["label"], "חורף 2026 — העיצוב החדש")
        self.assertIn("emails/winter2026/hero_bg.jpg", data["html"])

        data = self.client.get(reverse("library_html", args=[f"campaign:{old.pk}"])).json()
        self.assertEqual(data["html"], old.html_content)

        response = self.client.get(reverse("library_preview", args=[f"campaign:{old.pk}"]))
        self.assertContains(response, "<p>שלום {{שם}}</p>")
        self.assertContains(response, "<!DOCTYPE html>")
        # Previews are embedded in an iframe on the same site
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(self.client.get(reverse("campaign_preview", args=[old.pk]))["X-Frame-Options"], "SAMEORIGIN")

        self.assertEqual(self.client.get(reverse("library_html", args=["tpl:nope"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("library_html", args=["campaign:999"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("library_html", args=["junk"])).status_code, 404)

    def test_library_requires_staff(self):
        self.client.logout()
        response = self.client.get(reverse("library_html", args=["tpl:winter_2026"]))
        self.assertEqual(response.status_code, 302)

    def test_admin_index_links_to_campaigns(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, reverse("campaign_list"))
        self.assertContains(response, "מערכת קמפיינים")
