import re

from django import forms

from .models import Campaign, Contact, ContactNote

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def parse_recipients(raw: str):
    """Parse a pasted list. Each line: 'email' or 'email, store name'.

    Returns list of (email, name) tuples, deduplicated by email.
    """
    seen = set()
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        match = EMAIL_RE.search(line)
        if not match:
            continue
        email = match.group(0).lower()
        name = line.replace(match.group(0), "").strip(" ,;<>\t-")
        if email not in seen:
            seen.add(email)
            result.append((email, name))
    return result


INCLUDE_REPEATS_LABEL = "לצרף גם חנויות שכבר קיבלו מייל בקמפיין קודם"


class CampaignForm(forms.ModelForm):
    recipients_raw = forms.CharField(
        label="רשימת נמענים",
        widget=forms.Textarea(attrs={
            "rows": 8,
            "placeholder": "shop1@gmail.com\nshop2@walla.co.il, בייבי דרימס\nכתובת אחת בכל שורה, אפשר להוסיף שם חנות אחרי פסיק",
        }),
        required=False,
        help_text="כתובת מייל אחת בכל שורה. אפשר להוסיף שם חנות אחרי פסיק - הוא יחליף {{שם}} במייל.",
    )
    include_repeats = forms.BooleanField(
        label=INCLUDE_REPEATS_LABEL, required=False,
        help_text="כברירת מחדל, מי שכבר נשלח אליו מייל בעבר מדולג אוטומטית כדי לא להטריד.",
    )

    class Meta:
        model = Campaign
        fields = ["name", "subject", "from_name", "html_content"]
        widgets = {
            "html_content": forms.Textarea(attrs={"rows": 14, "dir": "ltr", "style": "font-family: monospace; font-size: 12px;"}),
        }


class AddRecipientsForm(forms.Form):
    recipients_raw = forms.CharField(
        label="הוספת נמענים",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "shop@gmail.com, שם החנות"}),
    )
    include_repeats = forms.BooleanField(label=INCLUDE_REPEATS_LABEL, required=False)


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class ContactNoteForm(forms.ModelForm):
    class Meta:
        model = ContactNote
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 2, "placeholder": "לדוגמה: דיברתי עם המנהל, לחזור אליו בעוד שבוע"})}
        labels = {"text": "הוספת הערה ליומן"}


class TestEmailForm(forms.Form):
    email = forms.EmailField(label="שליחת מייל בדיקה אל", widget=forms.EmailInput(attrs={"placeholder": "you@gmail.com"}))
