import base64
import logging
import requests
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

SANDBOX_BASE = 'https://sandbox.safaricom.co.ke'
PRODUCTION_BASE = 'https://api.safaricom.co.ke'


def _base_url() -> str:
    return PRODUCTION_BASE if settings.MPESA_ENVIRONMENT == 'production' else SANDBOX_BASE


def get_access_token() -> str:
    key    = settings.MPESA_CONSUMER_KEY.strip()
    secret = settings.MPESA_CONSUMER_SECRET.strip()
    logger.error("Daraja auth attempt — key_len=%d secret_len=%d env=%s", len(key), len(secret), settings.MPESA_ENVIRONMENT)
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    resp = requests.get(url, auth=(key, secret), timeout=15)
    if not resp.ok:
        logger.error("Daraja auth failed [%s]: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    return resp.json()['access_token']


def _password_and_timestamp() -> tuple[str, str]:
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f"{settings.MPESA_BUSINESS_SHORT_CODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def query_stk_push(checkout_request_id: str) -> dict:
    """Query the status of a pending STK Push transaction."""
    token              = get_access_token()
    password, timestamp = _password_and_timestamp()

    payload = {
        "BusinessShortCode": settings.MPESA_BUSINESS_SHORT_CODE,
        "Password":          password,
        "Timestamp":         timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    resp = requests.post(
        f"{_base_url()}/mpesa/stkpushquery/v1/query",
        json=payload,
        headers=headers,
        timeout=30,
    )
    logger.error("Daraja STK query response [%s]: %s", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()


def initiate_stk_push(phone_number: str, amount: int, order_id, description: str) -> dict:
    """
    Send a CustomerBuyGoodsOnline STK Push.

    Till flow:
      BusinessShortCode = Till Number (shown on customer's phone)
      PartyB            = Till Number
      TransactionType   = CustomerBuyGoodsOnline
    """
    token              = get_access_token()
    password, timestamp = _password_and_timestamp()
    account_ref        = f"ORDER-{str(order_id)[:8].upper()}"

    payload = {
        "BusinessShortCode": settings.MPESA_BUSINESS_SHORT_CODE,
        "Password":          password,
        "Timestamp":         timestamp,
        "TransactionType":   "CustomerBuyGoodsOnline",
        "Amount":            amount,
        "PartyA":            phone_number,
        "PartyB":            settings.MPESA_TILL_NUMBER,
        "PhoneNumber":       phone_number,
        "CallBackURL":       settings.MPESA_CALLBACK_URL,
        "AccountReference":  account_ref,
        "TransactionDesc":   description[:13],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    resp = requests.post(
        f"{_base_url()}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers,
        timeout=30,
    )
    logger.error("Daraja STK push response [%s]: %s", resp.status_code, resp.text)
    resp.raise_for_status()
    return resp.json()
