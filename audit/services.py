from audit.models import AdminAuditLog


def log_admin_action(*, action: str, actor=None, target=None, message: str = "", metadata: dict | None = None):
    return AdminAuditLog.objects.create(
        action=action,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        target_model=target.__class__.__name__ if target is not None else "",
        target_id=str(getattr(target, "pk", "")) if target is not None else "",
        message=message,
        metadata=metadata or {},
    )
