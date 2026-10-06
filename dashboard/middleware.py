from .models import StaffActionAudit


class StaffActionAuditMiddleware:
    """Record successful mutating requests made by platform staff."""

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and user.is_staff
            and request.method in self.WRITE_METHODS
            and response.status_code < 400
        ):
            match = getattr(request, "resolver_match", None)
            StaffActionAudit.objects.create(
                actor=user,
                route_name=getattr(match, "view_name", "") or "",
                method=request.method,
                response_status=response.status_code,
            )
        return response
