import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderSerializer
from mpesa.daraja import initiate_stk_push

logger = logging.getLogger(__name__)


def normalize_phone(raw: str) -> str:
    """Convert 07XXXXXXXX / +2547XXXXXXXX / 2547XXXXXXXX to 2547XXXXXXXX."""
    phone = raw.strip().replace(' ', '').replace('-', '').lstrip('+')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    return phone


class OrderCreateView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data       = serializer.validated_data
        items_data = data.pop('items')
        total      = sum(i['quantity'] * i['unit_price'] for i in items_data)
        phone      = normalize_phone(data['customer_phone'])

        order = Order.objects.create(
            customer_name    = data['customer_name'],
            customer_phone   = phone,
            delivery_address = data['delivery_address'],
            total_amount     = total,
        )
        for item in items_data:
            OrderItem.objects.create(order=order, **item)

        try:
            result = initiate_stk_push(
                phone_number = phone,
                amount       = int(total),
                order_id     = order.id,
                description  = "Createch Kit",
            )

            if result.get('ResponseCode') == '0':
                order.mpesa_checkout_request_id = result.get('CheckoutRequestID', '')
                order.mpesa_merchant_request_id = result.get('MerchantRequestID', '')
                order.save(update_fields=['mpesa_checkout_request_id', 'mpesa_merchant_request_id'])
                return Response({
                    'order_id':            str(order.id),
                    'checkout_request_id': order.mpesa_checkout_request_id,
                    'message':             'Check your phone for the M-Pesa prompt.',
                }, status=status.HTTP_201_CREATED)

            order.status = Order.FAILED
            order.mpesa_failure_reason = result.get('errorMessage', 'STK push rejected.')
            order.save(update_fields=['status', 'mpesa_failure_reason'])
            return Response(
                {'error': 'Could not send payment prompt. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception as exc:
            logger.error("STK push error for order %s: %s", order.id, exc)
            order.status = Order.FAILED
            order.save(update_fields=['status'])
            return Response(
                {'error': 'Payment service unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class OrderDetailView(APIView):
    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related('items').get(id=order_id)
        except (Order.DoesNotExist, ValueError):
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


class OrderListView(APIView):
    """Protected admin endpoint — requires X-API-Key header."""
    def get(self, request):
        key = request.headers.get('X-API-Key', '')
        if not settings.ADMIN_API_KEY or key != settings.ADMIN_API_KEY:
            return Response({'error': 'Unauthorised.'}, status=status.HTTP_401_UNAUTHORIZED)
        orders = Order.objects.prefetch_related('items').all()[:200]
        return Response(OrderSerializer(orders, many=True).data)
