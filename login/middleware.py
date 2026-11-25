from django.utils.cache import add_never_cache_headers


class PrivatePageCacheMiddleware:
    """Keep authenticated HTML out of the HTTP cache and shared proxies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, 'user', None) and request.user.is_authenticated:
            if response.get('Content-Type', '').startswith('text/html'):
                add_never_cache_headers(response)
        return response


class TwoFactorSessionMiddleware:
    """No HTTP endpoint may use an authenticated-but-unverified session."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.respond(request)
        if request.path.startswith('/usuarios/seguranca/'):
            response['Referrer-Policy'] = 'strict-origin'
            add_never_cache_headers(response)
        return response

    def respond(self, request):
        from django.contrib.auth import logout
        from django.http import JsonResponse
        from django.shortcuts import redirect
        from login import security
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and user.two_factor_enabled and request.session.get('mfa_version') != user.security_version:
            backend = request.session.get('_auth_user_backend', 'django.contrib.auth.backends.ModelBackend')
            logout(request)
            security.begin_login(request, user, backend)
            if request.path.startswith('/api/'):
                return JsonResponse({'detail': 'Confirme o segundo fator no login.'}, status=403)
            return redirect('two_factor_challenge')
        if user and user.is_authenticated and request.path.startswith(('/usuarios/perfil/dispositivos/', '/o/authorize/')) and not security.recent(request):
            request.session['security_return'] = request.get_full_path()
            return redirect('security_reauthenticate')
        return self.get_response(request)
