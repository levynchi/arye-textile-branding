from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import WhiteCatalogUser


class WhiteCatalogAdminBridgeTests(TestCase):
    def setUp(self):
        self.django_admin = get_user_model().objects.create_user(
            username="admin",
            password="lior1234",
            is_staff=True,
            is_superuser=True,
        )

    def test_white_catalog_login_accepts_django_admin_credentials(self):
        response = self.client.post(
            reverse("white_catalog:login"),
            {
                "username": "admin",
                "password": "lior1234",
                "next": reverse("white_catalog:cart"),
            },
        )

        self.assertRedirects(response, reverse("white_catalog:cart"))
        catalog_user = WhiteCatalogUser.objects.get(username="admin")
        self.assertEqual(self.client.session["white_catalog_user_id"], catalog_user.id)
        self.assertTrue(catalog_user.check_password("lior1234"))
        self.assertTrue(catalog_user.is_active)

    def test_logged_in_django_admin_can_open_catalog_without_separate_login(self):
        self.client.force_login(self.django_admin)

        response = self.client.get(reverse("white_catalog:cart"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(WhiteCatalogUser.objects.filter(username="admin", is_active=True).exists())

