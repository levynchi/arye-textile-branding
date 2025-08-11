from django import forms
from .models import ContactRequest

class ContactRequestForm(forms.ModelForm):
    class Meta:
        model = ContactRequest
        fields = ["full_name", "company", "email", "phone", "message"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "שם מלא"}),
            "company": forms.TextInput(attrs={"placeholder": "חברה"}),
            "email": forms.EmailInput(attrs={"placeholder": "אימייל"}),
            "phone": forms.TextInput(attrs={"placeholder": "טלפון"}),
            "message": forms.Textarea(attrs={"placeholder": "תיאור הבקשה", "rows": 6}),
        }
