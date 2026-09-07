from django.db import models


class Contact(models.Model):
    """A store/customer card - one per email address, shared across campaigns."""

    class Status(models.TextChoices):
        NEW = "new", "חדש"
        CONTACTED = "contacted", "נשלח מייל"
        REPLIED = "replied", "הגיב"
        IN_TALKS = "in_talks", "בשיחה"
        CUSTOMER = "customer", "לקוח"
        NOT_INTERESTED = "not_interested", "לא מעוניין"

    email = models.EmailField("אימייל", unique=True)
    name = models.CharField("שם החנות", max_length=200, blank=True)
    status = models.CharField("סטטוס", max_length=20, choices=Status.choices, default=Status.NEW)
    notes = models.TextField("הערות", blank=True)
    last_contacted_at = models.DateTimeField("פנייה אחרונה", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "לקוח"
        verbose_name_plural = "לקוחות"

    def __str__(self):
        return self.name or self.email

    @property
    def campaigns_sent(self):
        """Recipients of this contact that were actually sent, newest first."""
        return (
            Recipient.objects.filter(contact=self, status=Recipient.Status.SENT)
            .select_related("campaign")
            .order_by("-sent_at")
        )

    @classmethod
    def get_or_create_for(cls, email: str, name: str = ""):
        contact, created = cls.objects.get_or_create(email=email.lower(), defaults={"name": name})
        if not created and name and not contact.name:
            contact.name = name
            contact.save(update_fields=["name", "updated_at"])
        return contact


class ContactNote(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="contact_notes")
    text = models.TextField("הערה")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "הערת לקוח"
        verbose_name_plural = "הערות לקוח"

    def __str__(self):
        return f"{self.contact} - {self.created_at:%d/%m/%Y}"


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "טיוטה"
        SENDING = "sending", "בשליחה"
        DONE = "done", "הסתיים"

    name = models.CharField("שם הקמפיין", max_length=200)
    subject = models.CharField("נושא המייל", max_length=300)
    from_name = models.CharField("שם השולח", max_length=120, default="Arye Textile")
    html_content = models.TextField("תוכן HTML")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "קמפיין"
        verbose_name_plural = "קמפיינים"

    def __str__(self):
        return self.name

    @property
    def total_count(self):
        return self.recipients.count()

    @property
    def sent_count(self):
        return self.recipients.filter(status=Recipient.Status.SENT).count()

    @property
    def failed_count(self):
        return self.recipients.filter(status=Recipient.Status.FAILED).count()

    @property
    def pending_count(self):
        return self.recipients.filter(status=Recipient.Status.PENDING).count()


class Recipient(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "ממתין"
        SENT = "sent", "נשלח"
        FAILED = "failed", "נכשל"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipients")
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="recipients",
    )
    email = models.EmailField("אימייל")
    name = models.CharField("שם החנות", max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    message_id = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        ordering = ["id"]
        unique_together = [("campaign", "email")]
        verbose_name = "נמען"
        verbose_name_plural = "נמענים"

    def __str__(self):
        return self.email

    @property
    def is_repeat(self):
        """True if this email was already sent a campaign email before this one."""
        qs = Recipient.objects.filter(email=self.email, status=Recipient.Status.SENT).exclude(pk=self.pk)
        if self.sent_at:
            qs = qs.filter(sent_at__lt=self.sent_at)
        return qs.exists()


class Reply(models.Model):
    """An incoming email reply pulled from the Gmail inbox."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="replies")
    recipient = models.ForeignKey(
        Recipient, on_delete=models.SET_NULL, null=True, blank=True, related_name="replies",
    )
    from_email = models.EmailField("מאת")
    subject = models.CharField("נושא", max_length=500, blank=True)
    body = models.TextField("תוכן", blank=True)
    message_id = models.CharField(max_length=255, unique=True)
    received_at = models.DateTimeField("התקבל בתאריך")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "תגובה"
        verbose_name_plural = "תגובות"

    def __str__(self):
        return f"{self.from_email}: {self.subject[:50]}"

    @property
    def campaign(self):
        return self.recipient.campaign if self.recipient else None
