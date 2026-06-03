import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from orders.models import Order
from .daraja import query_stk_push

logger = logging.getLogger(__name__)


class MpesaCallbackView(APIView):
    """
    Safaricom calls this URL after the customer completes (or cancels) payment.
    Always respond 200 with ResultCode 0 — Safaricom retries on any other response.
    """
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        try:
            stk = request.data['Body']['stkCallback']
            checkout_id = stk['CheckoutRequestID']
            result_code = stk['ResultCode']

            try:
                order = Order.objects.get(mpesa_checkout_request_id=checkout_id)
            except Order.DoesNotExist:
                logger.warning("Callback for unknown CheckoutRequestID: %s", checkout_id)
                return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

            if result_code == 0:
                items = stk.get('CallbackMetadata', {}).get('Item', [])
                receipt = next(
                    (i['Value'] for i in items if i['Name'] == 'MpesaReceiptNumber'), ''
                )
                order.status               = Order.PAID
                order.mpesa_receipt_number = receipt
                order.save(update_fields=['status', 'mpesa_receipt_number'])
                logger.info("Order %s paid — receipt %s", order.id, receipt)
            else:
                reason = stk.get('ResultDesc', 'Payment declined.')
                order.status               = Order.FAILED
                order.mpesa_failure_reason = reason
                order.save(update_fields=['status', 'mpesa_failure_reason'])
                logger.info("Order %s failed — %s", order.id, reason)

        except Exception as exc:
            logger.error("Callback processing error: %s", exc, exc_info=True)

        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


class PaymentStatusView(APIView):
    """
    GET /api/mpesa/status/<order_id>/
    Frontend polls this to check payment state. If the order is still pending,
    it queries Safaricom's STK Push Query API to get the latest result in case
    the callback was delayed.
    """
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except (Order.DoesNotExist, ValueError):
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status not in (Order.PENDING,):
            return Response({
                'order_id':       str(order.id),
                'status':         order.status,
                'receipt':        order.mpesa_receipt_number,
                'failure_reason': order.mpesa_failure_reason,
            })

        if order.mpesa_checkout_request_id:
            try:
                result      = query_stk_push(order.mpesa_checkout_request_id)
                result_code = result.get('ResultCode')

                if result_code in (0, '0'):
                    order.status = Order.PAID
                    order.save(update_fields=['status'])
                    logger.info("Order %s marked paid via STK query", order.id)
                elif result_code is not None and str(result_code) not in ('', 'None'):
                    order.status               = Order.FAILED
                    order.mpesa_failure_reason = result.get('ResultDesc', 'Payment failed.')
                    order.save(update_fields=['status', 'mpesa_failure_reason'])
                    logger.info("Order %s marked failed via STK query — %s", order.id, order.mpesa_failure_reason)
            except Exception as exc:
                logger.warning("STK query failed for order %s: %s", order.id, exc)

        return Response({
            'order_id':       str(order.id),
            'status':         order.status,
            'receipt':        order.mpesa_receipt_number,
            'failure_reason': order.mpesa_failure_reason,
        })
