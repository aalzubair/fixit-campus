"""Views for FixIt Campus (Presentation layer, the C in MVC).

Each view reads the request, checks login and role, validates with a form,
calls ONE service function and chooses a template or a redirect. The IUB
ID number is kept in the session between the steps of registration and of
password reset; the services never see the session. Starting and ending
the session (log in, log out) also happens only here.
"""

from collections.abc import Callable
from functools import wraps
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from campus.constants import (
    HOME_PAGE_TEXT,
    MSG_NEW_OTP_SENT,
    MSG_NOT_AUTHORIZED,
    MSG_PASSWORD_CHANGED,
    MSG_RESET_OTP_SENT,
    SESSION_REGISTER_ID_NUMBER,
    SESSION_RESET_ID_NUMBER,
    TEMPLATE_FORBIDDEN,
    TEMPLATE_HOME,
    TEMPLATE_LOGIN,
    TEMPLATE_PASSWORD_RESET,
    TEMPLATE_PASSWORD_RESET_VERIFY,
    TEMPLATE_REGISTER,
    TEMPLATE_REGISTER_DONE,
    TEMPLATE_REGISTER_VERIFY,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_PASSWORD_RESET,
    URL_NAME_PASSWORD_RESET_VERIFY,
    URL_NAME_REGISTER,
    URL_NAME_REGISTER_DONE,
    URL_NAME_REGISTER_VERIFY,
)
from campus.forms import (
    LoginForm,
    OtpForm,
    PasswordResetRequestForm,
    PasswordResetVerifyForm,
    RegisterForm,
)
from campus.services import (
    ServiceError,
    log_in_user,
    register_user,
    request_new_registration_otp,
    request_password_reset,
    reset_password,
    verify_registration_otp,
)

ViewFunction = Callable[..., HttpResponse]


# --- Access control ---


def role_required(*roles: str) -> Callable[[ViewFunction], ViewFunction]:
    """Allow a view only for logged-in users with one of the given roles (FR-02).

    Not logged in: redirect to the login page. Wrong role: HTTP 403 with
    the "not authorized" message. ``never_cache`` is applied to every
    answer, so the back button after logout never shows the page.

    Args:
        roles: The role constants that may open the view.

    Returns:
        A decorator for a view function.
    """

    def decorator(view: ViewFunction) -> ViewFunction:
        """Wrap one view with the login, role and no-cache checks.

        Args:
            view: The view function to protect.

        Returns:
            The protected view function.
        """

        @wraps(view)
        def protected_view(
            request: HttpRequest, *args: object, **kwargs: object
        ) -> HttpResponse:
            """Show the view only to a user with an allowed role.

            Args:
                request: The HTTP request of a logged-in user.
                args: Positional URL arguments for the view.
                kwargs: Keyword URL arguments for the view.

            Returns:
                The view's response, or the 403 page.
            """
            if request.user.role not in roles:
                return render(
                    request,
                    TEMPLATE_FORBIDDEN,
                    {"message": MSG_NOT_AUTHORIZED},
                    status=HTTPStatus.FORBIDDEN,
                )
            return view(request, *args, **kwargs)

        return never_cache(login_required(protected_view))

    return decorator


# --- FR-01 Register ---


def register_view(request: HttpRequest) -> HttpResponse:
    """Show the registration form and register the user on submit (FR-01).

    Args:
        request: The HTTP request.

    Returns:
        The registration page, or a redirect to the OTP page on success.
    """
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        id_number = form.cleaned_data["id_number"]
        try:
            register_user(id_number, form.cleaned_data["password"])
        except ServiceError as error:
            form.add_error(None, error.message)
        else:
            request.session[SESSION_REGISTER_ID_NUMBER] = id_number
            return redirect(URL_NAME_REGISTER_VERIFY)
    return render(request, TEMPLATE_REGISTER, {"form": form})


def register_verify_view(request: HttpRequest) -> HttpResponse:
    """Show the OTP form and activate the account on a correct OTP (FR-01).

    Args:
        request: The HTTP request.

    Returns:
        The OTP page, a redirect to the success page, or a redirect to the
        registration page if the user has not registered in this session.
    """
    id_number = request.session.get(SESSION_REGISTER_ID_NUMBER)
    if id_number is None:
        return redirect(URL_NAME_REGISTER)
    form = OtpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            verify_registration_otp(id_number, form.cleaned_data["otp"])
        except ServiceError as error:
            form.add_error(None, error.message)
        else:
            del request.session[SESSION_REGISTER_ID_NUMBER]
            return redirect(URL_NAME_REGISTER_DONE)
    return render(request, TEMPLATE_REGISTER_VERIFY, {"form": form})


@require_POST
def register_new_otp_view(request: HttpRequest) -> HttpResponse:
    """Send a new registration OTP, then go back to the OTP page (FR-01).

    POST only, because it changes data (it cancels the earlier OTP).

    Args:
        request: The HTTP request.

    Returns:
        A redirect to the OTP page (with a success or error message), or
        to the registration page if the user has not registered in this
        session.
    """
    id_number = request.session.get(SESSION_REGISTER_ID_NUMBER)
    if id_number is None:
        return redirect(URL_NAME_REGISTER)
    try:
        request_new_registration_otp(id_number)
    except ServiceError as error:
        messages.error(request, error.message)
    else:
        messages.success(request, MSG_NEW_OTP_SENT)
    return redirect(URL_NAME_REGISTER_VERIFY)


def register_done_view(request: HttpRequest) -> HttpResponse:
    """Show the page that confirms the account is activated.

    Args:
        request: The HTTP request.

    Returns:
        The success page.
    """
    return render(request, TEMPLATE_REGISTER_DONE)


# --- FR-02 Log in, FR-03 Log out ---


def login_view(request: HttpRequest) -> HttpResponse:
    """Show the login form and start the session on success (FR-02).

    Args:
        request: The HTTP request.

    Returns:
        The login page, or a redirect to the home page when logged in.
    """
    if request.user.is_authenticated:
        return redirect(URL_NAME_HOME)
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = log_in_user(
                form.cleaned_data["id_number"], form.cleaned_data["password"]
            )
        except ServiceError as error:
            form.add_error(None, error.message)
        else:
            login(request, user)
            return redirect(URL_NAME_HOME)
    return render(request, TEMPLATE_LOGIN, {"form": form})


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    """End the session and show the login page (FR-03).

    POST only, so a link or an image on another site cannot log a user out.

    Args:
        request: The HTTP request.

    Returns:
        A redirect to the login page.
    """
    logout(request)
    return redirect(URL_NAME_LOGIN)


@never_cache
@login_required
def home_view(request: HttpRequest) -> HttpResponse:
    """Show the home page for the user's role (FR-02).

    Args:
        request: The HTTP request of a logged-in user.

    Returns:
        The home page with the heading and text for the user's role.
    """
    texts_by_role = {role: (heading, text) for role, heading, text in HOME_PAGE_TEXT}
    heading, text = texts_by_role[request.user.role]
    return render(request, TEMPLATE_HOME, {"heading": heading, "text": text})


# --- FR-04 Reset password ---


def password_reset_view(request: HttpRequest) -> HttpResponse:
    """Ask for the IUB ID number and send a password-reset OTP (FR-04).

    The same message is shown whether or not the ID is registered, so the
    page never reveals which IDs exist.

    Args:
        request: The HTTP request.

    Returns:
        The reset page, or a redirect to the OTP page.
    """
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        id_number = form.cleaned_data["id_number"]
        try:
            request_password_reset(id_number)
        except ServiceError as error:
            form.add_error(None, error.message)
        else:
            request.session[SESSION_RESET_ID_NUMBER] = id_number
            messages.info(request, MSG_RESET_OTP_SENT)
            return redirect(URL_NAME_PASSWORD_RESET_VERIFY)
    return render(request, TEMPLATE_PASSWORD_RESET, {"form": form})


def password_reset_verify_view(request: HttpRequest) -> HttpResponse:
    """Change the password with the OTP and the new password (FR-04).

    Args:
        request: The HTTP request.

    Returns:
        The OTP page, a redirect to the login page on success, or a
        redirect to the reset page if no reset was started in this session.
    """
    id_number = request.session.get(SESSION_RESET_ID_NUMBER)
    if id_number is None:
        return redirect(URL_NAME_PASSWORD_RESET)
    form = PasswordResetVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reset_password(
                id_number, form.cleaned_data["otp"], form.cleaned_data["new_password"]
            )
        except ServiceError as error:
            form.add_error(None, error.message)
        else:
            del request.session[SESSION_RESET_ID_NUMBER]
            messages.success(request, MSG_PASSWORD_CHANGED)
            return redirect(URL_NAME_LOGIN)
    return render(request, TEMPLATE_PASSWORD_RESET_VERIFY, {"form": form})


@require_POST
def password_reset_new_otp_view(request: HttpRequest) -> HttpResponse:
    """Send a new password-reset OTP, then go back to the OTP page (FR-04).

    POST only, because it changes data (it cancels the earlier OTP).

    Args:
        request: The HTTP request.

    Returns:
        A redirect to the OTP page (with a success or error message), or
        to the reset page if no reset was started in this session.
    """
    id_number = request.session.get(SESSION_RESET_ID_NUMBER)
    if id_number is None:
        return redirect(URL_NAME_PASSWORD_RESET)
    try:
        request_password_reset(id_number)
    except ServiceError as error:
        messages.error(request, error.message)
    else:
        messages.success(request, MSG_NEW_OTP_SENT)
    return redirect(URL_NAME_PASSWORD_RESET_VERIFY)
