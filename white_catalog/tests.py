import base64
import io
import json
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    WhiteCatalogUser,
    WhiteCategory,
    WhiteColor,
    WhiteColorVariant,
    WhiteFabricType,
    WhitePackType,
    WhiteProductVariant,
    WhiteSizeType,
    WhiteSubcategory,
    WhiteSubcategoryImage,
)
from .views import _product_gallery_images


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


@override_settings(WHITE_CATALOG_API_TOKEN="test-token", MEDIA_ROOT=tempfile.mkdtemp())
class ImportColorVariantsTests(TestCase):
    """ייבוא שורות צבע מהתוכנה השולחנית אל 'צבעים למוצר'."""

    def setUp(self):
        self.product = WhiteSubcategory.objects.create(name="סדין למיטת תינוק")
        self.url = reverse("white_catalog:api_import_variants")

    def _post(self, rows, fabric="טריקו ג'רזי"):
        return self.client.post(
            self.url,
            data=json.dumps({"product_id": self.product.id, "fabric_type": fabric, "rows": rows}),
            content_type="application/json",
            headers={"X-API-Token": "test-token"},
        )

    @staticmethod
    def _jpeg_b64():
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (600, 600), (115, 135, 168)).save(buf, "JPEG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def test_color_rows_create_color_variants_without_size(self):
        rows = [
            {"barcode": "7297555022264", "unit_price": "21.3", "color": "תכלת קשי", "color_hex": "#7387a8"},
            {"barcode": "7297555022271", "unit_price": "21.3", "color": "ורוד קשי", "color_hex": "#FFA4A4"},
        ]
        response = self._post(rows)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["created"], 2)
        self.assertEqual(WhiteColorVariant.objects.filter(product=self.product).count(), 2)
        tchelet = WhiteColorVariant.objects.get(barcode="7297555022264")
        self.assertEqual(tchelet.color.name, "תכלת קשי")
        self.assertEqual(tchelet.color.hex_color, "#7387a8")
        self.assertEqual(str(tchelet.unit_price), "21.30")
        # המוצר סומן אוטומטית להזמנה לפי מניפת צבעים
        self.product.refresh_from_db()
        self.assertTrue(self.product.has_color_variants)
        self.assertTrue(self.product.is_orderable)
        # לא נוצרו וריאנטים לפי מידה מהשורות האלה
        self.assertEqual(WhiteProductVariant.objects.count(), 0)

    def test_color_rows_are_idempotent_and_update_price(self):
        self._post([{"barcode": "111", "unit_price": "20", "color": "תכלת"}])
        response = self._post([{"barcode": "111", "unit_price": "25", "color": "תכלת"}])

        data = response.json()
        self.assertEqual(data["created"], 0)
        self.assertEqual(data["updated"], 1)
        variant = WhiteColorVariant.objects.get(barcode="111")
        self.assertEqual(str(variant.unit_price), "25.00")
        self.assertEqual(WhiteColorVariant.objects.count(), 1)
        self.assertEqual(WhiteColor.objects.count(), 1)

    def test_color_row_saves_variant_image_and_color_swatch(self):
        rows = [{
            "barcode": "222",
            "unit_price": "21.3",
            "color": "תכלת",
            "color_hex": "#7387a8",
            "image_base64": self._jpeg_b64(),
            "image_format": "jpg",
        }]
        response = self._post(rows)

        self.assertEqual(response.json()["errors"], [])
        variant = WhiteColorVariant.objects.get(barcode="222")
        self.assertTrue(variant.image)
        self.assertTrue(variant.image.name.endswith(".jpg"))
        # התמונה נשמרת גם כדוגמית הצבע במניפה
        color = WhiteColor.objects.get(name="תכלת")
        self.assertTrue(color.swatch_image)
        self.assertTrue(color.swatch_image.name.endswith(".jpg"))
        self.product.refresh_from_db()
        self.assertTrue(self.product.image)
        self.assertTrue(self.product.image.name.endswith(".jpg"))

    def test_color_import_switches_product_from_order_variants_to_color_mode(self):
        self.product.has_order_variants = True
        self.product.save(update_fields=["has_order_variants"])

        response = self._post([{"barcode": "666", "unit_price": "21.3", "color": "תכלת"}])

        data = response.json()
        self.assertEqual(data["errors"], [])
        self.product.refresh_from_db()
        self.assertTrue(self.product.has_color_variants)
        self.assertFalse(self.product.has_order_variants)
        self.assertTrue(any("כובה" in w for w in data["warnings"]))

    def test_color_row_releases_barcode_from_stale_size_variant(self):
        fabric = WhiteFabricType.objects.create(name="טריקו ג'רזי")
        size = WhiteSizeType.objects.create(name="66x128")
        WhiteProductVariant.objects.create(
            product=self.product, fabric_type=fabric, size_type=size, barcode="333"
        )

        response = self._post([{"barcode": "333", "unit_price": "21.3", "color": "שמנת"}])

        self.assertEqual(response.json()["errors"], [])
        self.assertTrue(WhiteColorVariant.objects.filter(barcode="333").exists())
        stale = WhiteProductVariant.objects.get(product=self.product)
        self.assertIsNone(stale.barcode)

    def test_color_row_conflicting_barcode_on_other_product_is_rejected(self):
        other = WhiteSubcategory.objects.create(name="מוצר אחר")
        color = WhiteColor.objects.create(name="לבן")
        WhiteColorVariant.objects.create(product=other, color=color, barcode="444")

        response = self._post([{"barcode": "444", "unit_price": "10", "color": "לבן"}])

        data = response.json()
        self.assertEqual(data["created"], 0)
        self.assertEqual(len(data["errors"]), 1)
        self.assertIn("444", data["errors"][0])

    def test_clear_image_keeps_hex_only_display(self):
        rows = [{
            "barcode": "222",
            "unit_price": "21.3",
            "color": "תכלת",
            "color_hex": "#7387a8",
            "image_base64": self._jpeg_b64(),
            "image_format": "jpg",
        }]
        self._post(rows)
        variant = WhiteColorVariant.objects.get(barcode="222")
        self.assertTrue(variant.image)
        self.assertTrue(variant.color.swatch_image)

        response = self._post([{
            "barcode": "222",
            "unit_price": "21.3",
            "color": "תכלת",
            "color_hex": "#7387a8",
            "clear_image": True,
        }])
        self.assertEqual(response.json()["errors"], [])
        variant.refresh_from_db()
        color = WhiteColor.objects.get(name="תכלת")
        self.assertFalse(variant.image)
        self.assertFalse(color.swatch_image)
        self.assertEqual(color.hex_color, "#7387a8")

    def test_delete_color_variant_by_barcode(self):
        color = WhiteColor.objects.create(name="אפור עשן בהיר")
        WhiteColorVariant.objects.create(product=self.product, color=color, barcode="7297555022295")

        response = self._post([{"barcode": "7297555022295", "delete": True}])

        data = response.json()
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["deleted"], 1)
        self.assertFalse(WhiteColorVariant.objects.filter(barcode="7297555022295").exists())

    def test_size_rows_still_work_as_before(self):
        rows = [
            {"size": "0-3", "barcode": "555", "unit_price": "12.5"},
            {"size": "3-6", "barcode": "556", "unit_price": "12.5"},
        ]
        response = self._post(rows)

        data = response.json()
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["created"], 2)
        self.assertEqual(WhiteProductVariant.objects.count(), 2)
        self.product.refresh_from_db()
        self.assertTrue(self.product.has_order_variants)
        self.assertFalse(self.product.has_color_variants)


class ClothingThreesOnlyTests(TestCase):
    """ביגוד מוזמן בשלישיות בלבד — חמישיות לא מוצעות ולא מתקבלות."""

    def setUp(self):
        self.threes = WhitePackType.objects.create(name="שלישיות", quantity=3, is_active=True)
        self.fives = WhitePackType.objects.create(name="חמישיות", quantity=5, is_active=True)
        self.user = WhiteCatalogUser.objects.create(
            company_name="בדיקה",
            contact_name="בודק",
            contact_phone="050",
            username="tester",
            pack_route=WhiteCatalogUser.ROUTE_FIVES,
        )
        self.user.set_password("pass")
        self.user.save()
        session = self.client.session
        session["white_catalog_user_id"] = self.user.id
        session["white_catalog_username"] = self.user.username
        session.save()

        self.product = WhiteSubcategory.objects.create(
            name="בגד גוף",
            is_orderable=True,
            has_order_variants=True,
        )
        fabric = WhiteFabricType.objects.create(name="טריקו")
        size = WhiteSizeType.objects.create(name="0-3")
        self.variant = WhiteProductVariant.objects.create(
            product=self.product,
            fabric_type=fabric,
            size_type=size,
            unit_price="12.00",
            barcode="111",
        )
        self.variant.pack_types.set([self.threes, self.fives])

    def test_allowed_pack_types_are_threes_even_if_user_route_is_fives(self):
        ids = list(self.user.get_allowed_pack_types().values_list("id", flat=True))
        self.assertEqual(ids, [self.threes.id])

    def test_cart_add_rejects_fives(self):
        response = self.client.post(
            reverse("white_catalog:cart_add"),
            {
                "format": "json",
                "pack_type_id": str(self.fives.id),
                f"qty_{self.variant.id}": "2",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("שלישיות", response.json()["error"])

    def test_cart_add_accepts_threes(self):
        response = self.client.post(
            reverse("white_catalog:cart_add"),
            {
                "format": "json",
                "pack_type_id": str(self.threes.id),
                f"qty_{self.variant.id}": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MergePrintedTetraPagesTests(TestCase):
    def setUp(self):
        self.category = WhiteCategory.objects.create(
            name="חיתולי בד / טטרה",
            slug="baby_diapers",
        )
        self.keep = WhiteSubcategory.objects.create(
            name="מארז 3 חיתולי טטרה - מודפס",
            slug="muslin_baby_diapers",
            category=self.category,
            is_orderable=True,
        )

    def test_legacy_hebrew_slug_redirects_to_muslin_page(self):
        response = self.client.get(
            reverse(
                "white_catalog:subcategory_detail",
                kwargs={
                    "category_slug": "baby_diapers",
                    "subcategory_slug": "מארז-חיתולי-טטרה-מודפס-3",
                },
            )
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.url,
            reverse(
                "white_catalog:subcategory_detail",
                kwargs={
                    "category_slug": "baby_diapers",
                    "subcategory_slug": "muslin_baby_diapers",
                },
            ),
        )

    def test_gallery_includes_product_and_print_images_without_duplicates(self):
        self.keep.image.save("main.jpg", ContentFile(b"main"), save=True)
        color = WhiteColor.objects.create(name="ינשופים כחול")
        variant = WhiteColorVariant.objects.create(product=self.keep, color=color)
        variant.image.save("print.jpg", ContentFile(b"print"), save=True)
        gallery = _product_gallery_images(self.keep)
        urls = [item["url"] for item in gallery]
        self.assertEqual(len(urls), 2)
        self.assertEqual(len(set(urls)), 2)
        self.assertTrue(any("main" in url for url in urls))
        self.assertTrue(any("print" in url for url in urls))

    def test_gallery_hides_same_photo_stored_as_different_files(self):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (80, 80), (200, 160, 140)).save(buf, "JPEG", quality=90)
        photo = buf.getvalue()
        extra = WhiteSubcategoryImage.objects.create(subcategory=self.keep, order=1)
        extra.image.save("gallery.jpg", ContentFile(photo), save=True)
        color = WhiteColor.objects.create(name="אוהלים וכוכבים ורוד")
        variant = WhiteColorVariant.objects.create(product=self.keep, color=color)
        variant.image.save("variant.jpg", ContentFile(photo), save=True)
        gallery = _product_gallery_images(self.keep)
        self.assertEqual(len(gallery), 1)

    def test_gallery_hides_reencoded_copy_of_the_same_photo(self):
        from PIL import Image

        src = Image.new("RGB", (120, 80), (40, 90, 140))
        src.paste((220, 180, 160), (20, 10, 70, 60))
        high = io.BytesIO()
        low = io.BytesIO()
        src.save(high, "JPEG", quality=92)
        src.resize((1400, 933)).save(low, "JPEG", quality=88)
        extra = WhiteSubcategoryImage.objects.create(subcategory=self.keep, order=1)
        extra.image.save("orig.jpg", ContentFile(high.getvalue()), save=True)
        color = WhiteColor.objects.create(name="סוסים וזיגזגים כחול")
        variant = WhiteColorVariant.objects.create(product=self.keep, color=color)
        variant.image.save("export.jpg", ContentFile(low.getvalue()), save=True)
        gallery = _product_gallery_images(self.keep)
        self.assertEqual(len(gallery), 1)

