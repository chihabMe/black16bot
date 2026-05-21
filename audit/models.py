from django.db import models


class AdminAuditLog(models.Model):
    action = models.CharField(max_length=120, db_index=True)
    actor = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="admin_audit_logs",
        on_delete=models.SET_NULL,
    )
    target_model = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.target_model}:{self.target_id}"
