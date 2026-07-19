import logging
import uuid
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Order
from .serializers import OrderSerializer
from .dpo import verify_token, DPOError, RESULT_NOT_PAID_YET

logger = logging.getLogger(__name__)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


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

class OrderDetailView(APIView):
    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related('items').get(id=order_id)
        except (Order.DoesNotExist, ValueError):
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


class PaymentStatusView(APIView):
    """GET /api/payment/status/?token=<dpo-transaction-token>

    Server-side verification of a DPO Pay transaction. The frontend return
    page calls this instead of trusting the ``CCDapproval`` param in DPO's
    redirect URL, which is not authenticated and can be forged.

    Returns only what the return page needs to render — never card data or
    customer PII from the DPO response.
    """

    def get(self, request):
        token = request.query_params.get('token', '').strip()
        if not _is_uuid(token):
            return Response({'error': 'A valid token query parameter is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            info = verify_token(token)
        except DPOError as exc:
            logger.error("DPO verifyToken failed for %s: %s", token, exc)
            return Response({'error': 'Could not verify payment. Please try again.'},
                            status=status.HTTP_502_BAD_GATEWAY)

        if info['paid']:
            payment_status = 'paid'
        elif info['result'] == RESULT_NOT_PAID_YET:
            payment_status = 'pending'
        else:
            payment_status = 'failed'

        return Response({
            'paid':     info['paid'],
            'status':   payment_status,
            'amount':   info['amount'],
            'currency': info['currency'],
        })
