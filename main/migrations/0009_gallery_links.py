from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_merge_20250829_0637"),
    ]

    operations = [
        migrations.AddField(
            model_name="gallery",
            name="link1",
            field=models.CharField(blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא", max_length=200, verbose_name="קישור 1"),
        ),
        migrations.AddField(
            model_name="gallery",
            name="link2",
            field=models.CharField(blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא", max_length=200, verbose_name="קישור 2"),
        ),
        migrations.AddField(
            model_name="gallery",
            name="link3",
            field=models.CharField(blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא", max_length=200, verbose_name="קישור 3"),
        ),
        migrations.AddField(
            model_name="gallery",
            name="link4",
            field=models.CharField(blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא", max_length=200, verbose_name="קישור 4"),
        ),
        migrations.AddField(
            model_name="gallery",
            name="link5",
            field=models.CharField(blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא", max_length=200, verbose_name="קישור 5"),
        ),
        migrations.AddField(
            model_name="gallery",
            name="link6",
            field=models.CharField(blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא", max_length=200, verbose_name="קישור 6"),
        ),
    ]
