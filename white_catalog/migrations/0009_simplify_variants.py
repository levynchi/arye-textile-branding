from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('white_catalog', '0008_whitesizetype_whitevariantsize_size_type'),
    ]

    operations = [
        # 1. Clear all unique_togethers that reference fields we're about to remove
        migrations.AlterUniqueTogether(
            name='whitecartitem',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='whitevariantpackprice',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='whiteproductvariant',
            unique_together=set(),
        ),
        # 2. Remove variant_size FK from WhiteCartItem
        migrations.RemoveField(
            model_name='whitecartitem',
            name='variant_size',
        ),
        # 3. Remove variant_size FK from WhiteVariantPackPrice
        migrations.RemoveField(
            model_name='whitevariantpackprice',
            name='variant_size',
        ),
        # 4. Delete WhiteVariantSize table (no more references)
        migrations.DeleteModel(
            name='WhiteVariantSize',
        ),
        # 5. Add size_type FK to WhiteProductVariant (nullable first)
        migrations.AddField(
            model_name='whiteproductvariant',
            name='size_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='product_variants',
                to='white_catalog.whitesizetype',
                verbose_name='מידה',
            ),
        ),
        # 6. Make size_type non-nullable (no existing rows)
        migrations.AlterField(
            model_name='whiteproductvariant',
            name='size_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='product_variants',
                to='white_catalog.whitesizetype',
                verbose_name='מידה',
            ),
        ),
        # 7. Add variant FK to WhiteVariantPackPrice (nullable first)
        migrations.AddField(
            model_name='whitevariantpackprice',
            name='variant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pack_prices',
                to='white_catalog.whiteproductvariant',
                verbose_name='גרסה',
            ),
        ),
        # 8. Make variant non-nullable
        migrations.AlterField(
            model_name='whitevariantpackprice',
            name='variant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pack_prices',
                to='white_catalog.whiteproductvariant',
                verbose_name='גרסה',
            ),
        ),
        # 9. Restore unique_togethers with new fields
        migrations.AlterUniqueTogether(
            name='whiteproductvariant',
            unique_together={('product', 'fabric_type', 'size_type')},
        ),
        migrations.AlterUniqueTogether(
            name='whitevariantpackprice',
            unique_together={('variant', 'pack_type')},
        ),
        migrations.AlterUniqueTogether(
            name='whitecartitem',
            unique_together={('cart', 'variant', 'pack_type')},
        ),
        # 10. Update model options
        migrations.AlterModelOptions(
            name='whiteproductvariant',
            options={
                'ordering': ('order', 'fabric_type__name', 'size_type__order'),
                'verbose_name': 'גרסת מוצר',
                'verbose_name_plural': 'גרסאות מוצר',
            },
        ),
        migrations.AlterModelOptions(
            name='whitevariantpackprice',
            options={
                'verbose_name': 'מחיר מארז',
                'verbose_name_plural': 'מחירי מארזים',
            },
        ),
    ]
