from django.contrib.admin import AdminSite
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode


class SecurityAdminSite(AdminSite):
    def has_permission(self, request):
        user = request.user
        return super().has_permission(request) and (
            not user.two_factor_enabled or request.session.get('mfa_version') == user.security_version
        )

    def login(self, request, extra_context=None):
        return redirect(reverse('login_user') + '?' + urlencode({'next': '/admin/'}))
