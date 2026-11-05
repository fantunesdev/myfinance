from rest_framework.permissions import BasePermission, SAFE_METHODS


class AuthenticatedReadStaffWrite(BasePermission):
    """Shared reference data can be read by users and changed only by staff."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and (request.method in SAFE_METHODS or request.user.is_staff)
        )
