from django.db import models


class BotRateLimit(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    action = models.CharField(max_length=80)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user_id", "action")
        indexes = [
            models.Index(fields=["user_id", "action"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.action}={self.count}"
