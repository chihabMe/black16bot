from time import monotonic


_BUCKETS: dict[tuple[int, str], list[float]] = {}


def is_rate_limited(user_id: int, action: str, *, limit: int = 12, window_seconds: int = 60) -> bool:
    now = monotonic()
    key = (user_id, action)
    recent = [stamp for stamp in _BUCKETS.get(key, []) if now - stamp < window_seconds]
    if len(recent) >= limit:
        _BUCKETS[key] = recent
        return True
    recent.append(now)
    _BUCKETS[key] = recent
    return False
