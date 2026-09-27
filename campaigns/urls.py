from django.urls import path

from . import views

urlpatterns = [
    path("", views.campaign_list, name="campaign_list"),
    path("new/", views.campaign_create, name="campaign_create"),
    path("<int:pk>/", views.campaign_detail, name="campaign_detail"),
    path("<int:pk>/edit/", views.campaign_edit, name="campaign_edit"),
    path("<int:pk>/preview/", views.campaign_preview, name="campaign_preview"),
    path("<int:pk>/send-test/", views.campaign_send_test, name="campaign_send_test"),
    path("<int:pk>/send/", views.campaign_send, name="campaign_send"),
    path("<int:pk>/add-recipients/", views.campaign_add_recipients, name="campaign_add_recipients"),
    path("<int:pk>/status/", views.campaign_status, name="campaign_status"),
    path("<int:pk>/delete/", views.campaign_delete, name="campaign_delete"),
    path("library/<str:key>/html/", views.library_html, name="library_html"),
    path("library/<str:key>/preview/", views.library_preview, name="library_preview"),
    path("contacts/", views.contact_list, name="contact_list"),
    path("contacts/<int:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/update/", views.contact_update, name="contact_update"),
    path("contacts/<int:pk>/add-note/", views.contact_add_note, name="contact_add_note"),
    path("replies/sync/", views.replies_sync, name="replies_sync"),
]
