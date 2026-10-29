
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles: tuple = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied("You do not have access to this area.")
        return super().dispatch(request, *args, **kwargs)


class OwnerScopedQuerysetMixin:
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(**{self.owner_field: self.request.user})


class StaffRequiredMixin(LoginRequiredMixin):
    """Requires login AND that the user is staff (any STAFF_ROLE) or superuser."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        from accounts.models import STAFF_ROLES
        if not (request.user.is_superuser or request.user.role in STAFF_ROLES):
            raise PermissionDenied("You do not have access to the management area.")
        return super().dispatch(request, *args, **kwargs)
