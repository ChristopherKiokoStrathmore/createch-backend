import uuid
from django.db import models


class Order(models.Model):
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (PENDING,    'Pending Payment'),
        (PAID,       'Paid'),
        (FAILED,     'Payment Failed'),
        (PROCESSING, 'Processing'),
        (SHIPPED,    'Shipped'),
        (DELIVERED,  'Delivered'),
        (CANCELLED,  'Cancelled'),
    ]

    id                       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_name            = models.CharField(max_length=200)
    customer_phone           = models.CharField(max_length=20)
    delivery_address         = models.TextField()
    status                   = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    total_amount             = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_checkout_request_id = models.CharField(max_length=200, blank=True)
    mpesa_merchant_request_id = models.CharField(max_length=200, blank=True)
    mpesa_receipt_number     = models.CharField(max_length=100, blank=True)
    mpesa_failure_reason     = models.CharField(max_length=500, blank=True)
    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{str(self.id)[:8].upper()} — {self.customer_name} ({self.get_status_display()})"


class OrderItem(models.Model):
    order        = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_id   = models.CharField(max_length=100)
    product_name = models.CharField(max_length=200)
    product_slug = models.CharField(max_length=200, blank=True)
    quantity     = models.PositiveIntegerField(default=1)
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity}× {self.product_name}"
