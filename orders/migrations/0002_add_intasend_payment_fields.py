from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                max_length=10,
                choices=[('mpesa', 'M-Pesa'), ('airtel', 'Airtel Money'), ('card', 'Card')],
                default='mpesa',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='intasend_invoice_id',
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name='order',
            name='intasend_failure_reason',
            field=models.CharField(max_length=500, blank=True),
        ),
        migrations.AddField(
            model_name='order',
            name='card_checkout_url',
            field=models.URLField(blank=True),
        ),
    ]
