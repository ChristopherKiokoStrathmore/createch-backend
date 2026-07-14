"""Thin client for the DPO Pay (3G Direct Pay) v6 XML API.

Only the piece this backend needs: verifying a transaction token
server-side, so the frontend return page never has to trust the
unauthenticated CCDapproval param in DPO's redirect URL.

Docs: https://docs.dpopay.com/api/
"""
import logging
import xml.etree.ElementTree as ET

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# DPO verifyToken result codes (see DPO response-code docs).
RESULT_PAID         = '000'   # Transaction Paid
RESULT_NOT_PAID_YET = '900'   # Token created, customer has not paid yet

_VERIFY_TEMPLATE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<API3G>'
    '<CompanyToken>{company_token}</CompanyToken>'
    '<Request>verifyToken</Request>'
    '<TransactionToken>{token}</TransactionToken>'
    '</API3G>'
)


class DPOError(Exception):
    """DPO API was unreachable or returned an unparseable body."""


def _text(root: ET.Element, tag: str, default: str = '') -> str:
    el = root.find(tag)
    return el.text.strip() if el is not None and el.text else default


def verify_token(transaction_token: str, timeout: int = 15) -> dict:
    """Ask DPO whether ``transaction_token`` has been paid.

    Returns a normalised dict::

        {'result', 'explanation', 'paid', 'amount', 'currency'}

    Raises :class:`DPOError` on network or parse failure. The caller is
    responsible for deciding what (if anything) to expose to the client.
    """
    if not settings.DPO_COMPANY_TOKEN:
        raise DPOError('DPO_COMPANY_TOKEN is not configured.')

    body = _VERIFY_TEMPLATE.format(
        company_token=settings.DPO_COMPANY_TOKEN,
        token=transaction_token,
    )
    try:
        resp = requests.post(
            settings.DPO_API_URL,
            data=body.encode('utf-8'),
            headers={'Content-Type': 'application/xml'},
            timeout=timeout,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except requests.RequestException as exc:
        raise DPOError(f'DPO request failed: {exc}') from exc
    except ET.ParseError as exc:
        raise DPOError(f'DPO returned unparseable XML: {exc}') from exc

    result = _text(root, 'Result')
    return {
        'result':      result,
        'explanation': _text(root, 'ResultExplanation'),
        'paid':        result == RESULT_PAID,
        'amount':      _text(root, 'TransactionAmount'),
        'currency':    _text(root, 'TransactionCurrency'),
    }
