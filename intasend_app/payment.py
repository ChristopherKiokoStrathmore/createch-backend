from intasend import APIService
from django.conf import settings


def _service() -> APIService:
    return APIService(
        token=settings.INTASEND_SECRET_KEY,
        publishable_key=settings.INTASEND_PUBLISHABLE_KEY,
        test=settings.INTASEND_TEST_MODE,
    )


def initiate_mpesa(phone_number: str, amount: int, order_id, narrative: str = "Createch Kit") -> dict:
    return _service().collect.mpesa_stk_push(
        phone_number=phone_number,
        email="",
        amount=amount,
        narrative=narrative,
        api_ref=str(order_id),
    )


def initiate_airtel(phone_number: str, amount: int, order_id, narrative: str = "Createch Kit") -> dict:
    return _service().collect.airtel(
        phone_number=phone_number,
        email="",
        amount=amount,
        narrative=narrative,
        api_ref=str(order_id),
    )


def initiate_card_checkout(amount: int, order_id, redirect_url: str) -> dict:
    """Returns a dict containing 'url' — redirect the customer there."""
    return _service().collect.checkout(
        phone_number="",
        email="",
        amount=amount,
        currency="KES",
        narrative="Createch Kit",
        api_ref=str(order_id),
        redirect_url=redirect_url,
    )
