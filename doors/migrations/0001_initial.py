from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Door',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(choices=[('main_entrance', 'Main Entrance'), ('interior', 'Interior'), ('bedroom', 'Bedroom'), ('bathroom', 'Bathroom'), ('office', 'Office'), ('commercial', 'Commercial'), ('safety', 'Safety Door')], max_length=50)),
                ('material', models.CharField(choices=[('solid_wood', 'Solid Wood'), ('engineered_wood', 'Engineered Wood'), ('steel', 'Steel'), ('glass', 'Glass & Wood'), ('fiber', 'Fiber'), ('pvc', 'PVC'), ('aluminium', 'Aluminium')], max_length=50)),
                ('description', models.TextField()),
                ('width', models.DecimalField(decimal_places=2, help_text='Width in mm', max_digits=6)),
                ('height', models.DecimalField(decimal_places=2, help_text='Height in mm', max_digits=6)),
                ('thickness', models.DecimalField(decimal_places=2, help_text='Thickness in mm', max_digits=5)),
                ('finish_type', models.CharField(choices=[('matte', 'Matte'), ('gloss', 'Gloss'), ('satin', 'Satin'), ('textured', 'Textured'), ('natural', 'Natural Wood'), ('lacquered', 'Lacquered')], max_length=50)),
                ('price_min', models.PositiveIntegerField(help_text='Minimum price in INR')),
                ('price_max', models.PositiveIntegerField(help_text='Maximum price in INR')),
                ('image_main', models.ImageField(upload_to='doors/')),
                ('image_2', models.ImageField(blank=True, null=True, upload_to='doors/')),
                ('image_3', models.ImageField(blank=True, null=True, upload_to='doors/')),
                ('image_4', models.ImageField(blank=True, null=True, upload_to='doors/')),
                ('features', models.TextField(blank=True, help_text='Enter features, one per line')),
                ('is_featured', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Inquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone', models.CharField(max_length=15)),
                ('email', models.EmailField(blank=True)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('quoted', 'Quoted'), ('closed', 'Closed')], default='new', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('door', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inquiries', to='doors.door')),
            ],
            options={'ordering': ['-created_at'], 'verbose_name_plural': 'Inquiries'},
        ),
        migrations.CreateModel(
            name='DoorPreview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('house_image', models.ImageField(upload_to='previews/house/')),
                ('preview_image', models.ImageField(blank=True, null=True, upload_to='previews/result/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('door', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='previews', to='doors.door')),
            ],
        ),
    ]
