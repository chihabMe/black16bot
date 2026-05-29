import uuid

from core.logging import clear_request_context, set_request_context


class RequestIDMiddleware:
    """Add unique request ID to each request and extract user context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4())[:8])
        request.request_id = request_id

        user_id = '-'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
        elif hasattr(request, 'telegram_user'):
            user_id = str(request.telegram_user.telegram_id)

        set_request_context(request_id=request_id, user_id=user_id)

        response = self.get_response(request)
        response['X-Request-ID'] = request_id

        clear_request_context()

        return response
