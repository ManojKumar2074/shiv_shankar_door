from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Changes from v1 → v2:
    - category:   removed 'safety' and 'interior', added 'pooja'
    - material:   renamed 'solid_wood' → 'hard_wood'
    - height:     changed from DecimalField to CharField with choices (inches)
    - width:      changed from DecimalField to CharField with choices (inches)
    - thickness:  changed from DecimalField to CharField with choices (mm)
    - finish_type: now stores comma-separated values (multi-finish support)
    - price_min/price_max: now nullable (Pooja only)
    - sft_rate:   new field — rate per sq.ft for non-Pooja doors
    """

    dependencies = [
        ('doors', '0001_initial'),
    ]

    operations = [
        # ── height: Decimal → CharField ──────────────────────
        migrations.AlterField(
            model_name='door',
            name='height',
            field=models.CharField(
                max_length=20,
                default='78',
                choices=[
                    ('72', '72 inches'), ('75', '75 inches'),
                    ('78', '78 inches'), ('81', '81 inches'),
                    ('84', '84 inches'), ('custom', 'As per customization'),
                ],
                help_text='Standard height in inches',
            ),
        ),
        # ── width: Decimal → CharField ───────────────────────
        migrations.AlterField(
            model_name='door',
            name='width',
            field=models.CharField(
                max_length=20,
                default='30',
                choices=[
                    ('26', '26 inches'), ('28', '28 inches'),
                    ('30', '30 inches'), ('32', '32 inches'),
                    ('34', '34 inches'), ('36', '36 inches'),
                    ('custom', 'As per customization'),
                ],
                help_text='Standard width in inches',
            ),
        ),
        # ── thickness: Decimal → CharField ───────────────────
        migrations.AlterField(
            model_name='door',
            name='thickness',
            field=models.CharField(
                max_length=10,
                default='32',
                choices=[('30', '30 mm'), ('32', '32 mm')],
                help_text='Thickness in mm',
            ),
        ),
        # ── finish_type: now comma-separated multi-value ─────
        migrations.AlterField(
            model_name='door',
            name='finish_type',
            field=models.CharField(
                max_length=200,
                help_text='One or more finishes, comma-separated (e.g. matte,gloss)',
            ),
        ),
        # ── price_min / price_max: nullable (Pooja only) ─────
        migrations.AlterField(
            model_name='door',
            name='price_min',
            field=models.PositiveIntegerField(
                null=True, blank=True,
                help_text='Pooja Room doors only — minimum price in ₹',
            ),
        ),
        migrations.AlterField(
            model_name='door',
            name='price_max',
            field=models.PositiveIntegerField(
                null=True, blank=True,
                help_text='Pooja Room doors only — maximum price in ₹',
            ),
        ),
        # ── sft_rate: new field ───────────────────────────────
        migrations.AddField(
            model_name='door',
            name='sft_rate',
            field=models.CharField(
                max_length=20,
                blank=True, null=True,
                choices=[
                    ('270', '₹270 per sq.ft'),
                    ('300', '₹300 per sq.ft'),
                    ('325', '₹325 per sq.ft'),
                    ('custom', 'Custom / On Request'),
                ],
                help_text='Rate per sq.ft — for all doors except Pooja Room',
            ),
        ),
    ]

