from api_access.models import DeveloperApiKey


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
