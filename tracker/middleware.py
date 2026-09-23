import logging
import traceback

logger = logging.getLogger('tracker.exceptions')


class ExceptionLoggingMiddleware:
    """
    Middleware that captures and logs all uncaught exceptions occurring
    during request processing with full traceback and request context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Extract request context
        user_info = getattr(request, 'user', 'Anonymous')
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
        
        logger.error(
            "Unhandled Exception at %s %s from IP %s (User: %s): %s\nTraceback:\n%s",
            request.method,
            request.get_full_path(),
            client_ip,
            user_info,
            str(exception),
            traceback.format_exc(),
            extra={
                'request_method': request.method,
                'request_path': request.get_full_path(),
                'client_ip': client_ip,
            }
        )
        # Return None so Django's default exception handling continues (e.g. 500 handler)
        return None
