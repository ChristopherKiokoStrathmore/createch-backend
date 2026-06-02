import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from orders.models import Order

logger = logging.getLogger(__name__)


class MpesaCallbackView(APIView):
    """
    Safaricom calls this URL after the customer completes (or cancels) payment.
    Always respond 200 with ResultCode 0 — Safaricom retries on any other response.
    """
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
