# Place this file in your doors/migrations/ folder
# Name it: 0002_alter_door_fields_multivalue.py  (or next number in sequence)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Change '0001_initial' to your last migration name
        ('doors', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='door',
            name='category',
            field=models.CharField(
                max_length=200,
                blank=True,
                help_text='One or more categories, comma-separated'
            ),
        ),
        migrations.AlterField(
            model_name='door',
            name='height',
            field=models.CharField(
                max_length=200,
                help_text='One or more heights, comma-separated'
            ),
        ),
        migrations.AlterField(
            model_name='door',
            name='width',
            field=models.CharField(
                max_length=200,
                help_text='One or more widths, comma-separated'
            ),
        ),
        migrations.AlterField(
            model_name='door',
            name='thickness',
            field=models.CharField(
                max_length=200,
                help_text='One or more thicknesses, comma-separated'
            ),
        ),
    ]