from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('white_catalog', '0009_simplify_variants'),
    ]

    operations = [
        migrations.AddField(
            model_name='whiteproductvariant',
            name='unit_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='מחיר ליחידה בודדת — המחיר למארז יחושב אוטומטית לפי הכמות',
                max_digits=10,
                null=True,
                verbose_name='מחיר ליחידה (לא כולל מע"מ)',
            ),
        ),
    ]
