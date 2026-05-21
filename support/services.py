from bot.telegram_client import notify_admins
from support.models import SupportTicket


def create_support_ticket(*, user_id: int, message: str) -> SupportTicket:
    ticket = SupportTicket.objects.create(user_id=user_id, message=message)
    notify_admins(
        "New support ticket\n\n"
        f"Ticket: #{ticket.pk}\n"
        f"User ID: {ticket.user.telegram_id}\n"
        f"Username: @{ticket.user.username or '-'}\n"
        f"Message: {message[:500]}"
    )
    return ticket
