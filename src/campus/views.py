"""Views for FixIt Campus (Presentation layer, the C in MVC).

Each view reads the request, validates with a form, calls ONE service
function and chooses a template or a redirect. The IUB ID number is kept
in the session between the registration pages; the services never see
the session.
"""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from campus.constants import (
    MSG_NEW_OTP_SENT,
    SESSION_REGISTER_ID_NUMBER,
    TEMPLATE_REGISTER,
    TEMPLATE_REGISTER_DONE,
    TEMPLATE_REGISTER_VERIFY,
    URL_NAME_REGISTER,
    URL_NAME_REGISTER_DONE,
    URL_NAME_REGISTER_VERIFY,
)
from campus.forms import OtpForm, RegisterForm
from campus.services import (
    RegistrationError,
    register_user,
    request_new_registration_otp,
    verify_registration_otp,
)


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
        except RegistrationError as error:
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
        except RegistrationError as error:
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
    except RegistrationError as error:
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
