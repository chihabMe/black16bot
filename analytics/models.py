from django.db import models
from django.conf import settings


class UserActivity(models.Model):
    """Track user activities for analytics."""

    class ActivityType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        TOPUP = "topup", "Top-up"
        SUPPORT_TICKET = "support_ticket", "Support Ticket"
        API_CALL = "api_call", "API Call"
        BOT_COMMAND = "bot_command", "Bot Command"
        LOGIN = "login", "Login"
        REFERRAL_SIGNUP = "referral_signup", "Referral Signup"

    user = models.ForeignKey(
        "accounts.TelegramUser",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    activity_type = models.CharField(
        max_length=32,
        choices=ActivityType.choices,
        db_index=True,
    )
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_activity_type_display()} at {self.created_at}"
