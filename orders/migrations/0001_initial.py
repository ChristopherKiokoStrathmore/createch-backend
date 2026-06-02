import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('customer_name', models.CharField(max_length=200)),
                ('customer_phone', models.CharField(max_length=20)),
                ('delivery_address', models.TextField()),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending Payment'),
                        ('paid', 'Paid'),
                        ('failed', 'Payment Failed'),
                        ('processing', 'Processing'),
                        ('shipped', 'Shipped'),
                        ('delivered', 'Delivered'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('mpesa_checkout_request_id', models.CharField(blank=True, max_length=200)),
                ('mpesa_merchant_request_id', models.CharField(blank=True, max_length=200)),
                ('mpesa_receipt_number', models.CharField(blank=True, max_length=100)),
                ('mpesa_failure_reason', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order')),
                ('product_id', models.CharField(max_length=100)),
                ('product_name', models.CharField(max_length=200)),
                ('product_slug', models.CharField(blank=True, max_length=200)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
    ]
