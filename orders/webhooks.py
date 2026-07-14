import base64
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Order, OrderItem

logger = logging.getLogger(__name__)

# Woo order status → our Order status. Raw Woo status is stored alongside.
WOO_STATUS_MAP = {
    'pending':        Order.PENDING,
    'on-hold':        Order.PENDING,
    'checkout-draft': Order.PENDING,
    'processing':     Order.PROCESSING,   # Woo "processing" = paid, awaiting fulfillment
    'completed':      Order.DELIVERED,
    'failed':         Order.FAILED,
    'cancelled':      Order.CANCELLED,
    'refunded':       Order.CANCELLED,
}


def _payment_method_from_gateway(gateway: str) -> str:
    gateway = (gateway or '').lower()
    if 'mpesa' in gateway:
        return Order.MPESA
    if 'airtel' in gateway:
        return Order.AIRTEL
    return Order.CARD


def _signature_valid(request) -> bool:
    """Woo signs each delivery: base64(HMAC-SHA256(secret, raw body))."""
    supplied = request.headers.get('X-WC-Webhook-Signature', '')
    if not supplied:
        return False
    expected = base64.b64encode(
        hmac.new(
            settings.WOO_WEBHOOK_SECRET.encode(),
            request.body,
            hashlib.sha256,
        ).digest()
    ).decode()
    return hmac.compare_digest(expected, supplied)


class WooWebhookView(APIView):
    """Receives WooCommerce order.created / order.updated webhooks and
    mirrors the order into our database (upsert by Woo order ID)."""

    def post(self, request):
        if not settings.WOO_WEBHOOK_SECRET:
            logger.error("Woo webhook received but WOO_WEBHOOK_SECRET is not set.")
            return Response({'error': 'Webhook not configured.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Woo sends a form-encoded ping (webhook_id=...) when the webhook is
        # first saved. Acknowledge anything that isn't an order payload
        # without touching the database.
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({'detail': 'Ping acknowledged.'})
        if not isinstance(payload, dict) or 'id' not in payload:
            return Response({'detail': 'Ignored: not an order payload.'})

        if not _signature_valid(request):
            logger.warning("Woo webhook signature mismatch (order %s).", payload.get('id'))
            return Response({'error': 'Invalid signature.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            order = self._upsert_order(payload)
        except Exception as exc:
            logger.error("Woo webhook processing failed: %s", exc, exc_info=True)
            return Response({'error': 'Processing failed.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'order_id': str(order.id), 'woo_order_id': order.woo_order_id})

    @transaction.atomic
    def _upsert_order(self, payload: dict) -> Order:
        billing  = payload.get('billing') or {}
        shipping = payload.get('shipping') or {}
        gateway  = payload.get('payment_method', '')

        name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip() or 'Unknown'
        address_src = shipping if shipping.get('address_1') else billing
        address = ', '.join(filter(None, [
            address_src.get('address_1', ''),
            address_src.get('address_2', ''),
            address_src.get('city', ''),
        ])) or 'N/A'

        woo_status = payload.get('status', '')
        order, _created = Order.objects.update_or_create(
            woo_order_id=payload['id'],
            defaults={
                'customer_name':       name,
                'customer_phone':      (billing.get('phone') or '').strip(),
                'customer_email':      billing.get('email') or '',
                'delivery_address':    address,
                'total_amount':        payload.get('total') or 0,
                'status':              WOO_STATUS_MAP.get(woo_status, Order.PENDING),
                'woo_status':          woo_status,
                'woo_payment_gateway': gateway,
                'payment_method':      _payment_method_from_gateway(gateway),
            },
        )

        order.items.all().delete()
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product_id=str(item.get('product_id', '')),
                product_name=item.get('name', ''),
                quantity=item.get('quantity', 1),
                unit_price=item.get('price') or 0,
            )
            for item in payload.get('line_items', [])
        ])
        return order
