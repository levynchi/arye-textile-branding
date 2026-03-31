from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('white_catalog', '0007_whitefabrictype_whiteproductvariant_fabric_type'),
    ]

    operations = [
        # 1. Create WhiteSizeType
        migrations.CreateModel(
            name='WhiteSizeType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='שם מידה')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='סדר תצוגה')),
                ('is_active', models.BooleanField(default=True, verbose_name='פעיל')),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'מידה',
                'verbose_name_plural': 'מידות',
                'ordering': ('order', 'name'),
                'app_label': 'white_catalog',
            },
        ),
        # 2. Remove old unique_together before field changes
        migrations.AlterUniqueTogether(
            name='whitevariantsize',
            unique_together=set(),
        ),
        # 3. Remove old size_name CharField
        migrations.RemoveField(
            model_name='whitevariantsize',
            name='size_name',
        ),
        # 4. Add size_type FK (nullable first)
        migrations.AddField(
            model_name='whitevariantsize',
            name='size_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='variant_sizes',
                to='white_catalog.whitesizetype',
                verbose_name='מידה',
            ),
        ),
        # 5. Make non-nullable (no existing rows)
        migrations.AlterField(
            model_name='whitevariantsize',
            name='size_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='variant_sizes',
                to='white_catalog.whitesizetype',
                verbose_name='מידה',
            ),
        ),
        # 6. Restore unique_together with new field
        migrations.AlterUniqueTogether(
            name='whitevariantsize',
            unique_together={('variant', 'size_type')},
        ),
        # 7. Update ordering
        migrations.AlterModelOptions(
            name='whitevariantsize',
            options={
                'ordering': ('order', 'size_type__order'),
                'verbose_name': 'מידה לגרסה',
                'verbose_name_plural': 'מידות לגרסה',
            },
        ),
    ]
