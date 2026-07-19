from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model  = OrderItem
        fields = ['product_id', 'product_name', 'product_slug', 'quantity', 'unit_price', 'subtotal']

    def get_subtotal(self, obj):
        return obj.subtotal


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_email',
            'delivery_address', 'status', 'total_amount', 'payment_method',
            'woo_order_id', 'woo_status', 'woo_payment_gateway',
            'mpesa_receipt_number', 'mpesa_failure_reason',
            'intasend_invoice_id', 'intasend_failure_reason',
            'card_checkout_url', 'items', 'created_at', 'updated_at',
        ]
