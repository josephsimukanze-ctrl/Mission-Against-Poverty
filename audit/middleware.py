# audit/middleware.py
class AuditRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._audit_ip = self._get_client_ip(request)
        request._audit_ua = request.META.get("HTTP_USER_AGENT", "")[:400]
        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
