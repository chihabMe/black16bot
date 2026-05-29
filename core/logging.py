import logging
import threading

_request_context = threading.local()


class RequestContextFilter(logging.Filter):
    """Add request_id and user_id to log records."""

    def filter(self, record):
        record.request_id = getattr(_request_context, 'request_id', '-')
        record.user_id = getattr(_request_context, 'user_id', '-')
        return True


def set_request_context(request_id=None, user_id=None):
    """Set request context for current thread."""
    if request_id is not None:
        _request_context.request_id = request_id
    if user_id is not None:
        _request_context.user_id = user_id


def clear_request_context():
    """Clear request context for current thread."""
    _request_context.request_id = '-'
    _request_context.user_id = '-'
