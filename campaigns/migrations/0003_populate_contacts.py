"""Create a Contact for every existing Recipient email and link them."""
from django.db import migrations


def populate_contacts(apps, schema_editor):
    Contact = apps.get_model("campaigns", "Contact")
    Recipient = apps.get_model("campaigns", "Recipient")

    for recipient in Recipient.objects.all().order_by("id"):
        email = recipient.email.lower()
        contact, created = Contact.objects.get_or_create(email=email, defaults={"name": recipient.name})
        if not created and recipient.name and not contact.name:
            contact.name = recipient.name
        if recipient.status == "sent":
            contact.status = "contacted" if contact.status == "new" else contact.status
            if recipient.sent_at and (contact.last_contacted_at is None or recipient.sent_at > contact.last_contacted_at):
                contact.last_contacted_at = recipient.sent_at
        contact.save()
        recipient.contact = contact
        recipient.save(update_fields=["contact"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0002_contact_recipient_message_id_recipient_contact_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_contacts, noop),
    ]
