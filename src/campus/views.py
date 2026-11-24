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
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from campus.constants import (
    COMPLAINANT_ROLES,
    HOME_PAGE_TEXT,
    MSG_COMPLAINT_NOT_ALLOWED,
    MSG_COMPLAINT_NOT_SAVED,
    MSG_COMPLAINT_REOPENED,
    MSG_FOLLOWING_STARTED,
    MSG_FOLLOWING_STOPPED,
    MSG_NEW_OTP_SENT,
    MSG_NO_COMPLAINTS,
    MSG_NO_FILTER_MATCH,
    MSG_NOT_AUTHORIZED,
    MSG_PASSWORD_CHANGED,
    MSG_REOPEN_EXPIRED,
    MSG_RESET_OTP_SENT,
    SESSION_REGISTER_ID_NUMBER,
    SESSION_RESET_ID_NUMBER,
    TAB_FOLLOWING,
    TAB_MY_COMPLAINTS,
    TEMPLATE_COMPLAINT_DETAIL,
    TEMPLATE_COMPLAINT_SUBMITTED,
    TEMPLATE_EXISTING_COMPLAINTS,
    TEMPLATE_FORBIDDEN,
    TEMPLATE_HOME,
    TEMPLATE_LOGIN,
    TEMPLATE_MY_COMPLAINTS,
    TEMPLATE_PASSWORD_RESET,
    TEMPLATE_PASSWORD_RESET_VERIFY,
    TEMPLATE_REGISTER,
    TEMPLATE_REGISTER_DONE,
    TEMPLATE_REGISTER_VERIFY,
    TEMPLATE_REOPEN_COMPLAINT,
    TEMPLATE_SIMILAR_COMPLAINTS,
    TEMPLATE_SUBMIT_COMPLAINT,
    URL_NAME_COMPLAINT_DETAIL,
    URL_NAME_COMPLAINT_SUBMITTED,
    URL_NAME_EXISTING_COMPLAINTS,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_MY_COMPLAINTS,
    URL_NAME_PASSWORD_RESET,
    URL_NAME_PASSWORD_RESET_VERIFY,
    URL_NAME_REGISTER,
    URL_NAME_REGISTER_DONE,
    URL_NAME_REGISTER_VERIFY,
)
from campus.forms import (
    BrowseFilterForm,
    CategoryLocationForm,
    ComplaintForm,
    LoginForm,
    OtpForm,
    PasswordResetRequestForm,
    PasswordResetVerifyForm,
    RegisterForm,
    ReopenForm,
)
from campus.services import (
    BrowseFilters,
    ComplaintDraft,
    ServiceError,
    browse_complaints,
    follow_complaint,
    get_complaint_detail,
    get_complaint_photo,
    get_similar_complaints,
    list_my_complaints,
    log_in_user,
    register_user,
    request_new_registration_otp,
    request_password_reset,
    reopen_complaint,
    reset_password,
    submit_complaint,
    unfollow_complaint,
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
    context = {
        "heading": heading,
        "text": text,
        "can_use_complaints": request.user.role in COMPLAINANT_ROLES,
    }
    return render(request, TEMPLATE_HOME, context)


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


# --- FR-06 to FR-10, FR-21 Complaints ---


def _forbidden(request: HttpRequest, message: str) -> HttpResponse:
    """Show the "access denied" page with HTTP 403.

    Args:
        request: The HTTP request.
        message: The user-facing message to show.

    Returns:
        The 403 response.
    """
    return render(
        request, TEMPLATE_FORBIDDEN, {"message": message}, status=HTTPStatus.FORBIDDEN
    )


def _following_tab_url() -> str:
    """Build the address of the Following tab of My Complaints.

    Returns:
        The My Complaints address with the Following tab selected.
    """
    return f"{reverse(URL_NAME_MY_COMPLAINTS)}?tab={TAB_FOLLOWING}"


@role_required(*COMPLAINANT_ROLES)
def submit_complaint_view(request: HttpRequest) -> HttpResponse:
    """Show the complaint form and save the complaint on submit (FR-06, FR-08).

    Args:
        request: The HTTP request of a complainant.

    Returns:
        The form page, or a redirect to the confirmation page after saving.
    """
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = submit_complaint(
                request.user, ComplaintDraft(**form.cleaned_data)
            )
            return redirect(
                URL_NAME_COMPLAINT_SUBMITTED, complaint_id=complaint.complaint_id
            )
    else:
        form = ComplaintForm()
    context = {"form": form, "not_saved_message": MSG_COMPLAINT_NOT_SAVED}
    return render(request, TEMPLATE_SUBMIT_COMPLAINT, context)


@role_required(*COMPLAINANT_ROLES)
@require_GET
def similar_complaints_view(request: HttpRequest) -> HttpResponse:
    """Show the "Already reported?" panel for a category and location (FR-07).

    Args:
        request: The HTTP request with ``category``, ``building``, ``floor``
            and ``room_or_area`` in the query string.

    Returns:
        The panel as a piece of HTML. Without a valid category and location
        it asks the user to choose them.
    """
    form = CategoryLocationForm(request.GET)
    similar = None
    if form.is_valid():
        similar = get_similar_complaints(request.user, **form.cleaned_data)
    return render(request, TEMPLATE_SIMILAR_COMPLAINTS, {"similar": similar})


@role_required(*COMPLAINANT_ROLES)
@require_GET
def complaint_submitted_view(request: HttpRequest, complaint_id: str) -> HttpResponse:
    """Confirm a saved complaint and show its ID (FR-06).

    Args:
        request: The HTTP request of the complaint's owner.
        complaint_id: The ID of the complaint that was just saved.

    Returns:
        The confirmation page, or the 403 page for someone else's complaint.
    """
    try:
        detail = get_complaint_detail(request.user, complaint_id)
    except ServiceError as error:
        return _forbidden(request, error.message)
    return render(
        request, TEMPLATE_COMPLAINT_SUBMITTED, {"complaint": detail.complaint}
    )


@role_required(*COMPLAINANT_ROLES)
@require_GET
def existing_complaints_view(request: HttpRequest) -> HttpResponse:
    """Browse Open and In Progress complaints with filters (FR-21).

    Args:
        request: The HTTP request; the filters are in the query string.

    Returns:
        The list page, with a message when nothing matches.
    """
    form = BrowseFilterForm(request.GET)
    filters = BrowseFilters(**form.cleaned_data) if form.is_valid() else BrowseFilters()
    has_filters = filters != BrowseFilters()
    context = {
        "form": form,
        "complaints": browse_complaints(request.user, filters),
        "has_filters": has_filters,
        "empty_message": MSG_NO_FILTER_MATCH if has_filters else MSG_NO_COMPLAINTS,
    }
    return render(request, TEMPLATE_EXISTING_COMPLAINTS, context)


@role_required(*COMPLAINANT_ROLES)
@require_GET
def my_complaints_view(request: HttpRequest) -> HttpResponse:
    """Show the user's own complaints and the ones they follow (FR-09).

    Args:
        request: The HTTP request; ``tab`` in the query string picks the list.

    Returns:
        The My Complaints page.
    """
    tab = (
        TAB_FOLLOWING if request.GET.get("tab") == TAB_FOLLOWING else TAB_MY_COMPLAINTS
    )
    context = {
        "tab": tab,
        "tab_mine": TAB_MY_COMPLAINTS,
        "tab_following": TAB_FOLLOWING,
        "my": list_my_complaints(request.user),
        "empty_message": MSG_NO_COMPLAINTS,
    }
    return render(request, TEMPLATE_MY_COMPLAINTS, context)


@role_required(*COMPLAINANT_ROLES)
@require_GET
def complaint_detail_view(request: HttpRequest, complaint_id: str) -> HttpResponse:
    """Show one of the user's own complaints (FR-09, FR-10).

    Args:
        request: The HTTP request of a complainant.
        complaint_id: The complaint ID from the address.

    Returns:
        The detail page, or the 403 page if it is not the user's complaint.
    """
    try:
        detail = get_complaint_detail(request.user, complaint_id)
    except ServiceError as error:
        return _forbidden(request, error.message)
    context = {"detail": detail, "expired_message": MSG_REOPEN_EXPIRED}
    return render(request, TEMPLATE_COMPLAINT_DETAIL, context)


@role_required(*COMPLAINANT_ROLES)
@require_GET
def complaint_photo_view(request: HttpRequest, complaint_id: str) -> HttpResponse:
    """Send the photo of the user's own complaint (NFR-05).

    Args:
        request: The HTTP request of a complainant.
        complaint_id: The complaint ID from the address.

    Returns:
        The image, the 403 page for someone else's complaint, or 404 when
        there is no photo.

    Raises:
        Http404: If the complaint has no photo or the file is missing.
    """
    try:
        photo = get_complaint_photo(request.user, complaint_id)
    except ServiceError as error:
        return _forbidden(request, error.message)
    if photo is None:
        raise Http404
    try:
        return FileResponse(photo.open("rb"))
    except FileNotFoundError as error:
        raise Http404 from error


@role_required(*COMPLAINANT_ROLES)
@require_POST
def follow_complaint_view(request: HttpRequest, complaint_id: str) -> HttpResponse:
    """Follow another user's complaint instead of duplicating it (FR-07).

    Args:
        request: The HTTP POST request of a complainant.
        complaint_id: The complaint ID from the address.

    Returns:
        A redirect to the Following tab, or to the browse page on an error.
    """
    try:
        follow_complaint(request.user, complaint_id)
    except ServiceError as error:
        messages.error(request, error.message)
        return redirect(URL_NAME_EXISTING_COMPLAINTS)
    messages.success(request, MSG_FOLLOWING_STARTED)
    return redirect(_following_tab_url())


@role_required(*COMPLAINANT_ROLES)
@require_POST
def unfollow_complaint_view(request: HttpRequest, complaint_id: str) -> HttpResponse:
    """Stop following a complaint (FR-09).

    Args:
        request: The HTTP POST request of a complainant.
        complaint_id: The complaint ID from the address.

    Returns:
        A redirect to the Following tab.
    """
    unfollow_complaint(request.user, complaint_id)
    messages.success(request, MSG_FOLLOWING_STOPPED)
    return redirect(_following_tab_url())


@role_required(*COMPLAINANT_ROLES)
def reopen_complaint_view(request: HttpRequest, complaint_id: str) -> HttpResponse:
    """Ask for a reason and reopen a Resolved complaint (FR-10).

    Args:
        request: The HTTP request of the complaint's owner.
        complaint_id: The complaint ID from the address.

    Returns:
        The reason form, or a redirect to the detail page. A complaint that
        cannot be reopened also goes back to the detail page, which explains why.
    """
    form = ReopenForm(request.POST) if request.method == "POST" else ReopenForm()
    if request.method == "POST" and form.is_valid():
        try:
            reopen_complaint(request.user, complaint_id, form.cleaned_data["reason"])
        except ServiceError as error:
            if error.message == MSG_COMPLAINT_NOT_ALLOWED:
                return _forbidden(request, error.message)
            messages.error(request, error.message)
        else:
            messages.success(request, MSG_COMPLAINT_REOPENED)
        return redirect(URL_NAME_COMPLAINT_DETAIL, complaint_id=complaint_id)
    try:
        detail = get_complaint_detail(request.user, complaint_id)
    except ServiceError as error:
        return _forbidden(request, error.message)
    if not detail.can_reopen:
        return redirect(URL_NAME_COMPLAINT_DETAIL, complaint_id=complaint_id)
    return render(request, TEMPLATE_REOPEN_COMPLAINT, {"form": form, "detail": detail})
