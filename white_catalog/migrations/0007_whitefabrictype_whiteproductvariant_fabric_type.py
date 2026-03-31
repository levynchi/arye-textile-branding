from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('white_catalog', '0006_whitepacktype_whitesubcategory_is_orderable_and_more'),
    ]

    operations = [
        # 1. Create WhiteFabricType
        migrations.CreateModel(
            name='WhiteFabricType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='שם הבד')),
                ('description', models.TextField(blank=True, verbose_name='תיאור הבד')),
                ('is_active', models.BooleanField(default=True, verbose_name='פעיל')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'סוג בד',
                'verbose_name_plural': 'סוגי בדים',
                'ordering': ('order', 'name'),
                'app_label': 'white_catalog',
            },
        ),
        # 2. Remove old unique_together before field changes
        migrations.AlterUniqueTogether(
            name='whiteproductvariant',
            unique_together=set(),
        ),
        # 3. Remove old fields from WhiteProductVariant
        migrations.RemoveField(
            model_name='whiteproductvariant',
            name='name',
        ),
        migrations.RemoveField(
            model_name='whiteproductvariant',
            name='description',
        ),
        # 4. Add fabric_type FK (nullable first so Django doesn't complain)
        migrations.AddField(
            model_name='whiteproductvariant',
            name='fabric_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='product_variants',
                to='white_catalog.whitefabrictype',
                verbose_name='סוג בד',
            ),
        ),
        # 5. Make fabric_type non-nullable (no existing rows so safe)
        migrations.AlterField(
            model_name='whiteproductvariant',
            name='fabric_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='product_variants',
                to='white_catalog.whitefabrictype',
                verbose_name='סוג בד',
            ),
        ),
        # 6. Add new unique_together
        migrations.AlterUniqueTogether(
            name='whiteproductvariant',
            unique_together={('product', 'fabric_type')},
        ),
        # 7. Update ordering
        migrations.AlterModelOptions(
            name='whiteproductvariant',
            options={
                'ordering': ('order', 'fabric_type__name'),
                'verbose_name': 'גרסת מוצר',
                'verbose_name_plural': 'גרסאות מוצר',
            },
        ),
    ]
