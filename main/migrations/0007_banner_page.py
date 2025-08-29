from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_slide"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="page",
            field=models.SlugField(blank=True, help_text="שם העמוד/slug (למשל: home, about, products). השאר ריק לבאנר כללי", max_length=50, null=True, verbose_name="עמוד"),
        ),
    ]
