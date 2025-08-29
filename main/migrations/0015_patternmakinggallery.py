from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0014_alter_printinggallery_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatternmakingGallery",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image1", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 1")),
                ("image2", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 2")),
                ("image3", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 3")),
                ("image4", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 4")),
                ("image5", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 5")),
                ("image6", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 6")),
                ("image7", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 7")),
                ("image8", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 8")),
                ("image9", models.ImageField(blank=True, null=True, upload_to="patternmaking_gallery/", verbose_name="תמונה 9")),
                ("updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "גלריית תדמיתנות וגזרנות",
                "verbose_name_plural": "גלריות תדמיתנות וגזרנות",
            },
        ),
    ]
