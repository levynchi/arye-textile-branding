from django.contrib import admin

from .models import Campaign, Contact, ContactNote, Recipient, Reply

admin.site.index_template = "admin/campaigns_index.html"
admin.site.site_header = "Arye Textile"
admin.site.index_title = "ניהול האתר"


class RecipientInline(admin.TabularInline):
    model = Recipient
    extra = 0
    readonly_fields = ("status", "error", "sent_at")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "status", "created_at")
    inlines = [RecipientInline]


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "campaign", "status", "sent_at")
    list_filter = ("status", "campaign")


class ContactNoteInline(admin.TabularInline):
    model = ContactNote
    extra = 0


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "status", "last_contacted_at")
    list_filter = ("status",)
    search_fields = ("email", "name")
    inlines = [ContactNoteInline]


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ("from_email", "subject", "contact", "received_at")
    list_filter = ("received_at",)
    search_fields = ("from_email", "subject", "body")
