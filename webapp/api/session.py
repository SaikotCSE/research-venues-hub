"""Session state and authentication: login, signup, logout, password reset/change, email verification.

Signing up and resetting a password both prove ownership of the email address with a one-time code
(see accounts/otp.py): step one emails the code, step two submits it.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from accounts import otp
from accounts.forms import SignUpForm
from accounts.verification import send_verification_email
from config.ratelimit import ratelimit
from venues.ownership import bookmarks_for

from .base import ApiError, endpoint, form_error, text

logger = logging.getLogger("venuepulse")
Purpose = otp.Purpose


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


# ------------------------------------------------------------------ email codes
def _issue(request, purpose, email, payload):
    try:
        return otp.issue(request, purpose, email, payload)
    except otp.CodeError as exc:
        raise ApiError(exc.message, exc.status) from None


def _verify(request, purpose):
    try:
        return otp.verify(request, purpose, text(request.data, "code", 20))
    except otp.CodeError as exc:
        raise ApiError(exc.message, exc.status, {"code": [exc.message]}) from None


def _code_sent(row, message):
    return {
        "ok": True,
        "email": row.email,
        "message": message,
        "expires_in": int(otp.CODE_TTL.total_seconds()),
        "resend_in": int(otp.RESEND_COOLDOWN.total_seconds()),
    }


def _send_signup_code(request, row, code):
    try:
        otp.send_code_email(row, code, name=row.payload["username"])
    except Exception:
        logger.exception("Could not send a sign-up code")
        otp.finish(request, row)  # let them retry straight away
        raise ApiError("We couldn't send the confirmation email right now. Please try again in a few minutes.", 503) from None


def _send_reset_code(row, code):
    user_id = row.payload.get("user")
    if user_id is None:  # no such account: nothing is sent, but the response is the same
        return
    user = get_user_model()._default_manager.select_related("profile").filter(pk=user_id).first()
    try:
        otp.send_code_email(row, code, name=user.profile.name if user else "")
    except Exception:
        logger.exception("Could not send a password reset code")


@ratelimit("email_code")
@endpoint("POST")
def resend_code(request):
    """Send a fresh code for the sign-up or password reset this browser started."""
    purpose = text(request.data, "purpose", 20)
    if purpose not in Purpose.values:
        raise ApiError("Unknown code type.", 400)
    row = otp.pending(request, purpose)
    if row is None:
        raise ApiError("This request has expired. Please start again.", 400)
    row, code = _issue(request, purpose, row.email, row.payload)
    if purpose == Purpose.SIGNUP:
        _send_signup_code(request, row, code)
        return _code_sent(row, f"We sent a new code to {row.email}.")
    _send_reset_code(row, code)
    return _code_sent(row, f"If an account uses {row.email}, we sent it a new code.")


# ------------------------------------------------------------------ sign-up
@ratelimit("signup")
@endpoint("POST")
def signup(request):
    """Step 1 of 2: validate the details and email a code. No account exists until the code is entered."""
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
    payload = {"username": form.cleaned_data["username"], "password": make_password(form.cleaned_data["password1"])}
    row, code = _issue(request, Purpose.SIGNUP, form.cleaned_data["email"], payload)
    _send_signup_code(request, row, code)
    return _code_sent(row, f"We sent a {otp.CODE_LENGTH}-digit code to {row.email}.")


@ratelimit("email_code")
@endpoint("POST")
def signup_verify(request):
    """Step 2 of 2: check the code, then create the account (email already confirmed) and log in."""
    if request.user.is_authenticated:
        raise ApiError("You are already signed in.", 400)
    row = _verify(request, Purpose.SIGNUP)
    User = get_user_model()
    username = row.payload["username"]
    taken = "That username or email address was registered while you were confirming. Please sign up again."
    if User.objects.filter(username__iexact=username).exists() or User.objects.filter(email__iexact=row.email).exists():
        otp.finish(request, row)
        raise ApiError(taken, 409)
    try:
        with transaction.atomic():
            user = User(username=username, email=row.email, password=row.payload["password"])
            user.save()
    except IntegrityError:
        otp.finish(request, row)
        raise ApiError(taken, 409) from None
    user.profile.verified_email = row.email
    user.profile.save(update_fields=["verified_email"])
    otp.finish(request, row)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    logger.info("New account registered: %s", user.pk)
    return {
        **session_payload(request, drain_messages=False),
        "next": safe_next(request, request.data.get("next"), reverse("accounts:profile")),
        "message": "Welcome to VenuePulse! Your email address is confirmed.",
    }


# ------------------------------------------------------------------ password reset
@ratelimit("password_reset")
@endpoint("POST")
def password_reset(request):
    """Step 1 of 2: email a reset code. The answer is the same whether or not an account uses the address."""
    email = text(request.data, "email", 254)
    try:
        validate_email(email)
    except ValidationError:
        raise ApiError("Please correct the highlighted fields.", 400, {"email": ["Enter a valid email address."]}) from None
    user = next(iter(PasswordResetForm().get_users(email)), None)  # active accounts with a usable password
    row, code = _issue(request, Purpose.PASSWORD_RESET, email, {"user": user.pk if user else None})
    _send_reset_code(row, code)
    return _code_sent(row, f"If an account uses {row.email}, we sent it a {otp.CODE_LENGTH}-digit code.")


@ratelimit("email_code")
@endpoint("POST")
def password_reset_confirm(request):
    """Step 2 of 2: check the code and set the new password. Changing it signs out the account's other sessions."""
    row = _verify(request, Purpose.PASSWORD_RESET)
    user_id = row.payload.get("user")
    user = get_user_model()._default_manager.filter(pk=user_id, is_active=True).first() if user_id else None
    if user is None or user.email.lower() != row.email:
        otp.finish(request, row)
        message = "This code is no longer valid. Request a new one."
        raise ApiError(message, 400, {"code": [message]})
    form = SetPasswordForm(user, data={"new_password1": request.data.get("new_password1", ""), "new_password2": request.data.get("new_password2", "")})
    if not form.is_valid():
        form_error(form)  # the code stays valid, so they can fix the password and resubmit
    form.save()
    otp.finish(request, row)
    logger.info("Password reset for user %s", user.pk)
    return {"ok": True}


# ------------------------------------------------------------------ signed in
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
