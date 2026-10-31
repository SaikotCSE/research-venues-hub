"""Session state and authentication: login, signup, logout, password reset/change, email verification."""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode

from accounts.forms import SignUpForm
from accounts.verification import send_verification_email
from config.ratelimit import ratelimit
from venues.ownership import bookmarks_for

from .base import ApiError, endpoint, form_error, text

logger = logging.getLogger("venuepulse")
RESET_SESSION_KEY = "_password_reset_token"


def session_payload(request, drain_messages=True):
    """Everything the app needs to render chrome for the current visitor."""
    user = request.user
    data = {
        "authenticated": user.is_authenticated,
        "csrf_token": get_token(request),
        "user": None,
        "unread_count": 0,
        "target_count": bookmarks_for(request).filter(is_starred=True).count(),
        "messages": [],
        "admin_url": None,
    }
    if drain_messages:
        data["messages"] = [{"level": m.level_tag or "info", "text": str(m)} for m in messages.get_messages(request)]
    if user.is_authenticated:
        p = user.profile
        data["user"] = {
            "username": user.get_username(),
            "email": user.email,
            "name": p.name,
            "initials": p.initials,
            "timezone": p.timezone,
            "email_verified": p.email_verified,
            "is_staff": user.is_staff,
        }
        data["unread_count"] = user.notifications.filter(read_at__isnull=True).count()
        if user.is_staff:
            data["admin_url"] = "/" + settings.ADMIN_URL
    return data


def safe_next(request, candidate, default):
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return default


@endpoint("GET")
def session(request):
    return session_payload(request)


@ratelimit("login")
@endpoint("POST")
def login_view(request):
    form = AuthenticationForm(request, data={"username": text(request.data, "username", 150), "password": request.data.get("password", "")})
    if not form.is_valid():
        form_error(form)
    login(request, form.get_user())
    return {**session_payload(request, drain_messages=False), "next": safe_next(request, request.data.get("next"), reverse("accounts:dashboard"))}


@endpoint("POST")
def logout_view(request):
    logout(request)
    return session_payload(request, drain_messages=False)


@ratelimit("signup")
@endpoint("POST")
def signup(request):
    if request.user.is_authenticated:
        raise ApiError("You are already signed in.", 400)
    form = SignUpForm(
        data={
            "username": text(request.data, "username", 150),
            "email": text(request.data, "email", 254),
            "password1": request.data.get("password1", ""),
            "password2": request.data.get("password2", ""),
        }
    )
    if not form.is_valid():
        form_error(form)
    user = form.save()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    logger.info("New account registered: %s", user.pk)
    send_verification_email(user, request)
    return {
        **session_payload(request, drain_messages=False),
        "next": safe_next(request, request.data.get("next"), reverse("accounts:profile")),
        "message": f"Welcome to VenuePulse! We sent a confirmation link to {user.email}.",
    }


@ratelimit("password_reset")
@endpoint("POST")
def password_reset(request):
    form = PasswordResetForm(data={"email": text(request.data, "email", 254)})
    if not form.is_valid():
        form_error(form)
    form.save(
        request=request,
        use_https=request.is_secure(),
        email_template_name="accounts/email/password_reset.txt",
        subject_template_name="accounts/email/password_reset_subject.txt",
    )
    # Same answer whether or not the address exists, so accounts cannot be enumerated.
    return {"ok": True}


def reset_user(uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return get_user_model()._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return None


@endpoint("POST")
def password_reset_confirm(request):
    """Set a new password; the reset token was stashed in the session by the link's landing view."""
    user = reset_user(text(request.data, "uid", 64))
    token = request.session.get(RESET_SESSION_KEY)
    if user is None or not token or not default_token_generator.check_token(user, token):
        raise ApiError("This password reset link is invalid or has already been used. Please request a new one.", 400)
    form = SetPasswordForm(user, data={"new_password1": request.data.get("new_password1", ""), "new_password2": request.data.get("new_password2", "")})
    if not form.is_valid():
        form_error(form)
    form.save()
    del request.session[RESET_SESSION_KEY]
    return {"ok": True}


@endpoint("POST", login=True)
def password_change(request):
    form = PasswordChangeForm(
        request.user,
        data={
            "old_password": request.data.get("old_password", ""),
            "new_password1": request.data.get("new_password1", ""),
            "new_password2": request.data.get("new_password2", ""),
        },
    )
    if not form.is_valid():
        form_error(form)
    form.save()
    update_session_auth_hash(request, form.user)
    return {"ok": True, "csrf_token": get_token(request)}


@ratelimit("verify_email")
@endpoint("POST", login=True)
def resend_verification(request):
    if request.user.profile.email_verified:
        return {"ok": True, "message": "Your email address is already confirmed."}
    if not send_verification_email(request.user, request):
        raise ApiError("Add an email address in account settings first.", 400)
    return {"ok": True, "message": f"We sent a new confirmation link to {request.user.email}."}
