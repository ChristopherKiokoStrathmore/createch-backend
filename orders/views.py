import logging
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Order, OrderItem
from .serializers import OrderCreateSerializer, OrderSerializer
from mpesa.daraja import initiate_stk_push
from intasend import payment as intasend

logger = logging.getLogger(__name__)


def normalize_phone(raw: str) -> str:
    """Convert 07XXXXXXXX / +2547XXXXXXXX / 2547XXXXXXXX to 2547XXXXXXXX."""
    phone = raw.strip().replace(' ', '').replace('-', '').lstrip('+')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    return phone


class OrderView(APIView):
    PAGE_SIZE = 20

    def get(self, request):
        key = request.headers.get('X-Admin-Key', '')
        if not settings.ADMIN_SECRET_KEY or key != settings.ADMIN_SECRET_KEY:
            return Response({'error': 'Unauthorised.'}, status=status.HTTP_401_UNAUTHORIZED)

        qs = Order.objects.prefetch_related('items').all()

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(mpesa_receipt_number__icontains=search) |
                Q(customer_phone__icontains=search) |
                Q(customer_name__icontains=search)
            )

        paginator   = Paginator(qs, self.PAGE_SIZE)
        page_number = request.query_params.get('page', 1)
        page        = paginator.get_page(page_number)

        return Response({
            'count':   paginator.count,
            'results': OrderSerializer(page.object_list, many=True).data,
        })

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data       = serializer.validated_data
        items_data = data.pop('items')
        total      = sum(i['quantity'] * i['unit_price'] for i in items_data)
        phone      = normalize_phone(data['customer_phone'])

        payment_method = data.get('payment_method', Order.MPESA)

        order = Order.objects.create(
            customer_name    = data['customer_name'],
            customer_phone   = phone,
            delivery_address = data['delivery_address'],
            total_amount     = total,
            payment_method   = payment_method,
        )
        for item in items_data:
            OrderItem.objects.create(order=order, **item)

        # ── IntaSend payments (M-Pesa, Airtel Money, Card) ───────────────────
        if settings.INTASEND_PUBLISHABLE_KEY and payment_method in (Order.MPESA, Order.AIRTEL, Order.CARD):
            try:
                if payment_method == Order.CARD:
                    redirect_url = f"{settings.FRONTEND_URL}/order-confirmation?id={order.id}"
                    result = intasend.initiate_card_checkout(int(total), order.id, redirect_url)
                    checkout_url = result.get("url") or result.get("checkout_url", "")
                    order.card_checkout_url = checkout_url
                    order.save(update_fields=["card_checkout_url"])
                    return Response({
                        "order_id":     str(order.id),
                        "checkout_url": checkout_url,
                        "message":      "Redirecting to card payment.",
                    }, status=status.HTTP_201_CREATED)

                elif payment_method == Order.AIRTEL:
                    result = intasend.initiate_airtel(phone, int(total), order.id)
                else:
                    result = intasend.initiate_mpesa(phone, int(total), order.id)

                invoice = result.get("invoice", {})
                order.intasend_invoice_id = invoice.get("invoice_id", "")
                order.save(update_fields=["intasend_invoice_id"])
                method_label = "M-Pesa" if payment_method == Order.MPESA else "Airtel Money"
                return Response({
                    "order_id": str(order.id),
                    "message":  f"Check your phone for the {method_label} prompt.",
                }, status=status.HTTP_201_CREATED)

            except Exception as exc:
                logger.error("IntaSend error for order %s: %s", order.id, exc)
                order.status = Order.FAILED
                order.save(update_fields=["status"])
                return Response(
                    {"error": "Payment service unavailable. Please try again."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        # ── Legacy M-Pesa Daraja (fallback when IntaSend not configured) ─────
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
