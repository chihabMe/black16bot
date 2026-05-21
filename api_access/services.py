from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from api_access.models import ApiUsageLog, DeveloperApiKey


def authenticate_api_key(raw_key: str) -> DeveloperApiKey | None:
    if not raw_key:
        return None
    key_hash = DeveloperApiKey.hash_key(raw_key)
    return (
        DeveloperApiKey.objects.select_related("user")
        .filter(key_hash=key_hash, is_active=True)
        .first()
    )


def revoke_user_api_keys(*, user_id: int) -> int:
    return DeveloperApiKey.objects.filter(user_id=user_id, is_active=True).update(is_active=False)


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def log_api_usage(
    *,
    api_key: DeveloperApiKey,
    request,
    endpoint: str,
    status_code: int,
    cost=0,
    error_code: str = "",
) -> ApiUsageLog:
    return ApiUsageLog.objects.create(
        api_key=api_key,
        endpoint=endpoint,
        method=request.method,
        status_code=status_code,
        cost=cost,
        error_code=error_code,
        request_ip=client_ip(request),
    )


def order_rate_limit_exceeded(api_key: DeveloperApiKey, *, endpoint: str = "orders.create") -> bool:
    if api_key.orders_per_minute <= 0:
        return False
    window_start = timezone.now() - timedelta(minutes=1)
    used = ApiUsageLog.objects.filter(
        api_key=api_key,
        endpoint=endpoint,
        created_at__gte=window_start,
    ).count()
    return used >= api_key.orders_per_minute


def daily_spend_used(api_key: DeveloperApiKey):
    day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    aggregate = ApiUsageLog.objects.filter(
        api_key=api_key,
        endpoint="orders.create",
        status_code__lt=400,
        created_at__gte=day_start,
    ).aggregate(total=Sum("cost"))
    return aggregate["total"] or 0
