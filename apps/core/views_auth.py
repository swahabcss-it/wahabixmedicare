from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from apps.core.models import AuditLog


def _client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR', 'unknown')


def _throttle_key(request):
    return f"login_attempts:{_client_ip(request)}:{request.POST.get('username', '')}"


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        key = _throttle_key(request)
        attempts = cache.get(key, 0)

        if attempts >= settings.LOGIN_ATTEMPT_LIMIT:
            messages.error(request, "Too many failed login attempts. Please try again in a few minutes.")
            AuditLog.log('Login blocked (rate limit)', details=f"ip={_client_ip(request)}", request=request)
            return render(request, 'base/login.html')

        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            cache.delete(key)
            login(request, user)
            AuditLog.log('User Login', user=user, request=request)
            return redirect('core:home')

        cache.set(key, attempts + 1, timeout=settings.LOGIN_ATTEMPT_WINDOW_SECONDS)
        AuditLog.log('Failed login attempt', details=f"ip={_client_ip(request)}, username={request.POST.get('username','')}", request=request)
        messages.error(request, 'Invalid username or password.')
    return render(request, 'base/login.html')

def logout_view(request):
    AuditLog.log('User Logout', user=request.user, request=request)
    logout(request)
    return redirect('auth:login')
