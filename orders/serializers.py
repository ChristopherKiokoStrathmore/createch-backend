from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    product_id   = serializers.CharField(max_length=100)
    product_name = serializers.CharField(max_length=200)
    product_slug = serializers.CharField(max_length=200, required=False, default='')
    quantity     = serializers.IntegerField(min_value=1, max_value=20)
    unit_price   = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderCreateSerializer(serializers.Serializer):
    customer_name    = serializers.CharField(max_length=200)
    customer_phone   = serializers.CharField(max_length=20)
    delivery_address = serializers.CharField()
    payment_method   = serializers.ChoiceField(choices=['mpesa', 'airtel', 'card'], default='mpesa')
    items            = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Cart is empty.")
        return value

    def validate_customer_phone(self, value):
        digits = value.strip().replace(' ', '').replace('-', '').replace('+', '')
        if not digits.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(digits) < 9 or len(digits) > 13:
            raise serializers.ValidationError("Enter a valid Kenyan phone number.")
        return value


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
