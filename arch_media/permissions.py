import hmac

from django.conf import settings


def _matches(supplied: str, secret: str) -> bool:
    if not supplied or not secret:
        return False
    a = supplied.encode('utf-8')
    b = secret.encode('utf-8')
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def is_arch_admin(request) -> bool:
    """True when X-Admin-Key matches ARCH_ADMIN_SECRET or ADMIN_SECRET_KEY."""
    key = request.headers.get('X-Admin-Key', '')
    return _matches(key, getattr(settings, 'ARCH_ADMIN_SECRET', '') or '') or _matches(
        key, getattr(settings, 'ADMIN_SECRET_KEY', '') or ''
    )
