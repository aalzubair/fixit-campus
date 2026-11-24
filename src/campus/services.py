"""Business rules for FixIt Campus (Application layer).

This module holds the rules for FR-01 (register with OTP verification),
FR-02 (log in, account lock, IUB records check) and FR-04 (reset password).
FR-03 (log out, idle timeout) only changes the session, so it lives in the
Presentation layer. This module never sees the request, the session or HTML.
Outside systems are used only through ``records.py`` (university records)
and ``delivery.py`` (sending the OTP).
"""

import secrets
import string
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from campus.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_LOCK_MINUTES,
    ACCOUNT_PENDING_ACTIVATION,
    LOGIN_MAX_FAILED_ATTEMPTS,
    MEMBER_NAME_MAX_LENGTH,
    MSG_ACCOUNT_LOCKED,
    MSG_ACCOUNT_NO_LONGER_ACTIVE,
    MSG_ALREADY_REGISTERED,
    MSG_ID_NOT_FOUND,
    MSG_INVALID_LOGIN,
    MSG_NO_CONTACT_DETAILS,
    MSG_OTP_EXPIRED,
    MSG_OTP_INCORRECT,
    MSG_OTP_NO_LONGER_VALID,
    MSG_PASSWORD_TOO_SHORT,
    MSG_TOO_MANY_REQUESTS,
    OTP_EXPIRED,
    OTP_INVALID,
    OTP_LENGTH,
    OTP_LIFETIME_MINUTES,
    OTP_MAX_WRONG_ATTEMPTS,
    OTP_PURPOSE_PASSWORD_RESET,
    OTP_PURPOSE_REGISTRATION,
    OTP_REQUEST_LIMIT,
    OTP_REQUEST_WINDOW_MINUTES,
    OTP_USED,
    OTP_VALID,
    PASSWORD_MIN_LENGTH,
)
from campus.delivery import get_otp_sender
from campus.models import Otp, User
from campus.records import UniversityMember, get_records_client


class ServiceError(Exception):
    """A service step (for example registration) was rejected by a business rule.

    Attributes:
        message: The user-facing message from ``constants.py``.
    """

    def __init__(self, message: str) -> None:
        """Store the user-facing message.

        Args:
            message: The user-facing message from ``constants.py``.
        """
        super().__init__(message)
        self.message = message


# --- Public service functions (called by views) ---


def register_user(id_number: str, password: str) -> None:
    """Register a university member and send them an OTP (FR-01).

    A new user is created as pending activation. If the user is already
    pending, the earlier password is replaced and a new OTP is sent.
    The name and role are copied from the university records.

    Args:
        id_number: The IUB ID number typed by the user.
        password: The chosen password in plain text.

    Raises:
        ServiceError: If the password is too short, the ID is not in
            the records, the ID has no contact details, the ID is already
            registered, or too many OTPs were requested.
    """
    _check_password_length(password)
    member, destination = _find_member_and_destination(id_number)
    # One transaction, so a rejected OTP request does not keep the new password.
    with transaction.atomic():
        user = _get_or_build_unregistered_user(id_number)
        _copy_records_details(user, member)
        user.set_password(password)
        user.mark_pending()
        user.save()
        _issue_otp(user, destination, OTP_PURPOSE_REGISTRATION)


def request_new_registration_otp(id_number: str) -> None:
    """Cancel the earlier registration OTP and send a new one (FR-01).

    Args:
        id_number: The IUB ID number of a user waiting for activation.

    Raises:
        ServiceError: If the user cannot be found or is already
            registered, the ID has no contact details any more, or too many
            OTPs were requested.
    """
    user = _get_pending_user(id_number)
    _, destination = _find_member_and_destination(id_number)
    with transaction.atomic():
        _issue_otp(user, destination, OTP_PURPOSE_REGISTRATION)


def verify_registration_otp(id_number: str, code: str) -> None:
    """Activate the account if the registration OTP is correct (FR-01).

    Args:
        id_number: The IUB ID number of a user waiting for activation.
        code: The OTP typed by the user.

    Raises:
        ServiceError: If the user cannot be found or is already
            registered, or the OTP is wrong, expired or no longer valid.
    """
    user = _get_pending_user(id_number)
    otp = _check_otp(user, OTP_PURPOSE_REGISTRATION, code)
    # One transaction, so the OTP is never used up without the account activating.
    with transaction.atomic():
        otp.status = OTP_USED
        otp.save()
        user.mark_active()
        user.save()


def log_in_user(id_number: str, password: str) -> User:
    """Check the ID and password and return the user who may log in (FR-02).

    The checks run in a fixed order: unknown or pending ID, lock, password,
    then the IUB records. The records are asked only after the correct
    password, so a wrong password never reveals whether a member has left.
    Starting the session is the view's job.

    No ``transaction.atomic()`` is used here on purpose: a wrong password
    must stay counted even though an error is raised afterwards.

    Args:
        id_number: The IUB ID number typed by the user.
        password: The password typed by the user.

    Returns:
        The user, with the name and role copied from the records and
        the wrong-password count cleared.

    Raises:
        ServiceError: If the ID or password is wrong, the account is
            locked, or the ID is no longer in the records.
    """
    now = timezone.now()
    user = _get_active_user(id_number)
    if user is None:
        raise ServiceError(MSG_INVALID_LOGIN)
    # Checked before the password, and nothing is counted while locked.
    if user.is_locked(now):
        raise ServiceError(MSG_ACCOUNT_LOCKED)
    if user.locked_until is not None:
        # The lock has run out, so counting wrong passwords starts again from 0.
        user.clear_lock()
    if not user.check_password(password):
        _record_failed_login(user, now)
        raise ServiceError(MSG_INVALID_LOGIN)
    member = get_records_client().find_member(id_number)
    if member is None:
        raise ServiceError(MSG_ACCOUNT_NO_LONGER_ACTIVE)
    # The records are the source of truth: a changed name or role takes effect now.
    _copy_records_details(user, member)
    user.clear_lock()
    user.save()
    return user


def request_password_reset(id_number: str) -> None:
    """Send a password-reset OTP to a registered member (FR-04).

    Unknown, pending and former members get no OTP and no error, so the
    page shows the same message for them as for a registered member.
    Also used by the "Request a new OTP" button, which cancels the
    earlier OTP.

    Args:
        id_number: The IUB ID number typed by the user.

    Raises:
        ServiceError: If the account is locked or too many OTPs were
            requested.
    """
    user = _get_active_user(id_number)
    if user is None:
        return
    try:
        _, destination = _find_member_and_destination(id_number)
    except ServiceError:
        # Left the university or no contact details: same answer as unknown.
        return
    if user.is_locked(timezone.now()):
        raise ServiceError(MSG_ACCOUNT_LOCKED)
    with transaction.atomic():
        _issue_otp(user, destination, OTP_PURPOSE_PASSWORD_RESET)


def reset_password(id_number: str, code: str, new_password: str) -> None:
    """Change the password if the password-reset OTP is correct (FR-04).

    The password length is checked first, so a too-short password does
    not use up one of the three OTP attempts. Changing the password does
    not unlock a locked account.

    Args:
        id_number: The IUB ID number the reset was requested for.
        code: The OTP typed by the user.
        new_password: The new password in plain text.

    Raises:
        ServiceError: If the new password is too short, or the OTP is
            wrong, expired or no longer valid.
    """
    _check_password_length(new_password)
    user = _get_active_user(id_number)
    if user is None:
        # Same message as a wrong OTP, so the page does not reveal the ID.
        raise ServiceError(MSG_OTP_INCORRECT)
    otp = _check_otp(user, OTP_PURPOSE_PASSWORD_RESET, code)
    # One transaction, so the OTP is never used up without the password changing.
    with transaction.atomic():
        otp.status = OTP_USED
        otp.save()
        user.set_password(new_password)
        user.save()


# --- Helpers: users and university records ---


def _check_password_length(password: str) -> None:
    """Reject a password shorter than the minimum length.

    Args:
        password: The chosen password in plain text.

    Raises:
        ServiceError: If the password is too short.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ServiceError(MSG_PASSWORD_TOO_SHORT)


def _find_member_and_destination(id_number: str) -> tuple[UniversityMember, str]:
    """Look up the ID in the records and choose where to send the OTP.

    The email is used first; the mobile number only if there is no email.

    Args:
        id_number: The IUB ID number to look up.

    Returns:
        The member from the records and their email or mobile number.

    Raises:
        ServiceError: If the ID is not in the records or has no
            contact details.
    """
    member = get_records_client().find_member(id_number)
    if member is None:
        raise ServiceError(MSG_ID_NOT_FOUND)
    destination = member.email or member.mobile
    if not destination:
        raise ServiceError(MSG_NO_CONTACT_DETAILS)
    return member, destination


def _copy_records_details(user: User, member: UniversityMember) -> None:
    """Copy the name and role from the university records (does not save).

    The full name goes into Django's existing ``first_name`` field and
    ``last_name`` is cleared, so ``get_full_name()`` returns exactly the
    records name without a new model field or migration. ``last_name`` is
    cleared because an account made another way (for example in the admin)
    may already have one. The name is stripped before it is cut, so outer
    spaces do not use up the field length, and stripped again after the cut,
    so a cut that ends on a space leaves no trailing space. A name longer
    than the field is cut, because a long name must not stop a member from
    registering or logging in.

    Args:
        user: The user to update.
        member: The same person in the university records.
    """
    user.first_name = member.name.strip()[:MEMBER_NAME_MAX_LENGTH].rstrip()
    user.last_name = ""
    user.role = member.role


def _raise_if_registered(user: User) -> None:
    """Reject a user whose account is no longer waiting for activation.

    Active accounts, locked or not, have finished registration.

    Args:
        user: The user to check.

    Raises:
        ServiceError: If the account is not pending activation.
    """
    if user.account_status != ACCOUNT_PENDING_ACTIVATION:
        raise ServiceError(MSG_ALREADY_REGISTERED)


def _get_or_build_unregistered_user(id_number: str) -> User:
    """Return the pending user for this ID, or a new unsaved user.

    Args:
        id_number: The IUB ID number.

    Returns:
        The existing pending user, or a new user that is not saved yet.

    Raises:
        ServiceError: If the ID is already registered.
    """
    user = User.objects.filter(username=id_number).first()
    if user is None:
        return User(username=id_number)
    _raise_if_registered(user)
    return user


def _get_pending_user(id_number: str) -> User:
    """Return the user for this ID who is waiting for activation.

    Args:
        id_number: The IUB ID number.

    Returns:
        The pending user.

    Raises:
        ServiceError: If no user has this ID, or the ID is already
            registered.
    """
    user = User.objects.filter(username=id_number).first()
    if user is None:
        raise ServiceError(MSG_ID_NOT_FOUND)
    _raise_if_registered(user)
    return user


def _get_active_user(id_number: str) -> User | None:
    """Return the activated user for this ID, or None.

    Args:
        id_number: The IUB ID number.

    Returns:
        The active user, or None if the ID is unknown or still pending.
    """
    return User.objects.filter(
        username=id_number, account_status=ACCOUNT_ACTIVE
    ).first()


def _record_failed_login(user: User, now: datetime) -> None:
    """Count a wrong password and lock the account on the last allowed try.

    Saved straight away, so the count and the lock stay stored after the
    caller raises its error.

    Args:
        user: The user who typed a wrong password.
        now: The current time.
    """
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = now + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
    user.save()


# --- Helpers: OTPs (written so FR-04 password reset can reuse them) ---


def _generate_otp_code() -> str:
    """Make a random numeric OTP with the ``secrets`` module.

    Returns:
        A string of ``OTP_LENGTH`` random digits.
    """
    return "".join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


def _check_request_limit(user: User, purpose: str, now: datetime) -> None:
    """Reject the request if the user asked for too many OTPs recently.

    Every OTP row of this purpose is one request, whatever its status.
    Each purpose has its own limit, so registration OTPs do not use up
    the password-reset limit.

    Args:
        user: The user asking for an OTP.
        purpose: One of the OTP purpose constants.
        now: The current time.

    Raises:
        ServiceError: If the limit for the time window is reached.
    """
    window_start = now - timedelta(minutes=OTP_REQUEST_WINDOW_MINUTES)
    recent_requests = Otp.objects.filter(
        user=user, purpose=purpose, created_at__gt=window_start
    )
    if recent_requests.count() >= OTP_REQUEST_LIMIT:
        raise ServiceError(MSG_TOO_MANY_REQUESTS)


def _issue_otp(user: User, destination: str, purpose: str) -> None:
    """Cancel the earlier valid OTP, then create and send a new one.

    Must be called inside ``transaction.atomic()`` so that a failed send
    does not leave a new OTP that the user never received.

    Args:
        user: The saved user who receives the OTP.
        destination: The email address or mobile number.
        purpose: One of the OTP purpose constants.

    Raises:
        ServiceError: If too many OTPs were requested.
    """
    now = timezone.now()
    _check_request_limit(user, purpose, now)
    # Only one OTP may be valid at a time, so the earlier one is cancelled.
    Otp.objects.filter(user=user, status=OTP_VALID).update(status=OTP_INVALID)
    code = _generate_otp_code()
    Otp.objects.create(
        user=user,
        purpose=purpose,
        code_hash=make_password(code),
        created_at=now,
        expires_at=now + timedelta(minutes=OTP_LIFETIME_MINUTES),
    )
    get_otp_sender().send_otp(destination, code)


def _check_otp(user: User, purpose: str, code: str) -> Otp:
    """Check a typed OTP against the user's valid OTP.

    This function only rejects or returns; it never marks the OTP used,
    so the caller decides what success means. Rejections are saved
    straight away (expired status, wrong-attempt count) so they still
    count after the error is raised.

    Args:
        user: The user who typed the OTP.
        purpose: One of the OTP purpose constants.
        code: The OTP typed by the user.

    Returns:
        The matching valid OTP, unchanged.

    Raises:
        ServiceError: If there is no valid OTP, or the OTP is expired
            or wrong.
    """
    otp = Otp.objects.filter(user=user, purpose=purpose, status=OTP_VALID).first()
    if otp is None:
        raise ServiceError(_missing_otp_message(user, purpose))
    if otp.is_expired(timezone.now()):
        otp.status = OTP_EXPIRED
        otp.save()
        raise ServiceError(MSG_OTP_EXPIRED)
    # check_password compares hashes in constant time.
    if not check_password(code, otp.code_hash):
        raise ServiceError(_record_wrong_attempt(otp))
    return otp


def _missing_otp_message(user: User, purpose: str) -> str:
    """Choose the message to show when the user has no valid OTP.

    The newest OTP tells why none is valid, so a user who submits again
    after expiry is told "expired" again, not "too many wrong attempts".

    Args:
        user: The user who typed the OTP.
        purpose: One of the OTP purpose constants.

    Returns:
        The expired message if the newest OTP expired, otherwise the
        no-longer-valid message.
    """
    newest_otp = Otp.objects.filter(user=user, purpose=purpose).first()
    if newest_otp is not None and newest_otp.status == OTP_EXPIRED:
        return MSG_OTP_EXPIRED
    return MSG_OTP_NO_LONGER_VALID


def _record_wrong_attempt(otp: Otp) -> str:
    """Count a wrong OTP and invalidate the OTP on the last allowed try.

    Args:
        otp: The OTP that was typed wrongly.

    Returns:
        The message to show: incorrect OTP, or no longer valid on the
        last allowed wrong attempt.
    """
    otp.wrong_attempts += 1
    if otp.wrong_attempts >= OTP_MAX_WRONG_ATTEMPTS:
        otp.status = OTP_INVALID
        otp.save()
        return MSG_OTP_NO_LONGER_VALID
    otp.save()
    return MSG_OTP_INCORRECT
