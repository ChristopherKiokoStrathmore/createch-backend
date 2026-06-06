import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from orders.models import Order

logger = logging.getLogger(__name__)


class IntaSendWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # IntaSend sends a challenge string when you first register the webhook URL.
        # We must echo it back or registration fails.
        challenge = request.data.get("challenge")
        if challenge:
            return Response({"challenge": challenge})

        try:
            invoice_id    = request.data.get("invoice_id", "")
            state         = request.data.get("state", "")
            api_ref       = request.data.get("api_ref", "")
            failed_reason = request.data.get("failed_reason") or ""

            if not api_ref:
                logger.warning("IntaSend webhook missing api_ref: %s", request.data)
                return Response({"status": "ok"})

            try:
                order = Order.objects.get(id=api_ref)
            except (Order.DoesNotExist, ValueError):
                logger.warning("IntaSend webhook for unknown order: %s", api_ref)
                return Response({"status": "ok"})

            if state == "COMPLETE":
                order.status               = Order.PAID
                order.intasend_invoice_id  = invoice_id
                order.save(update_fields=["status", "intasend_invoice_id"])
                logger.info("IntaSend: Order %s PAID (invoice %s)", order.id, invoice_id)

            elif state in ("FAILED", "CANCELLED"):
                order.status                    = Order.FAILED
                order.intasend_invoice_id       = invoice_id
                order.intasend_failure_reason   = failed_reason or state
                order.save(update_fields=["status", "intasend_invoice_id", "intasend_failure_reason"])
                logger.info("IntaSend: Order %s FAILED — %s", order.id, failed_reason)

        except Exception as exc:
            logger.error("IntaSend webhook error: %s", exc, exc_info=True)

        return Response({"status": "ok"})
