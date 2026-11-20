"""Business rules for FixIt Campus (Application layer).

This module holds the rules for FR-01 (register with OTP verification).
It never sees the request, the session or HTML. Outside systems are used
only through ``records.py`` (university records) and ``delivery.py``
(sending the OTP).
"""

import secrets
import string
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from campus.constants import (
    ACCOUNT_PENDING_ACTIVATION,
    MSG_ALREADY_REGISTERED,
    MSG_ID_NOT_FOUND,
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


class RegistrationError(Exception):
    """A registration step was rejected by a business rule.

    Attributes:
        message: The exact SRS message to show to the user.
    """

    def __init__(self, message: str) -> None:
        """Store the user-facing message.

        Args:
            message: The exact SRS message to show to the user.
        """
        super().__init__(message)
        self.message = message


# --- Public service functions (called by views) ---


def register_user(id_number: str, password: str) -> None:
    """Register a university member and send them an OTP (FR-01).

    A new user is created as pending activation. If the user is already
    pending, the earlier password is replaced and a new OTP is sent.

    Args:
        id_number: The IUB ID number typed by the user.
        password: The chosen password in plain text.

    Raises:
        RegistrationError: If the password is too short, the ID is not in
            the records, the ID has no contact details, the ID is already
            registered, or too many OTPs were requested.
    """
    _check_password_length(password)
    member, destination = _find_member_and_destination(id_number)
    # One transaction, so a rejected OTP request does not keep the new password.
    with transaction.atomic():
        user = _get_or_build_unregistered_user(id_number)
        user.role = member.role
        user.set_password(password)
        user.mark_pending()
        user.save()
        _issue_otp(user, destination, OTP_PURPOSE_REGISTRATION)


def request_new_registration_otp(id_number: str) -> None:
    """Cancel the earlier registration OTP and send a new one (FR-01).

    Args:
        id_number: The IUB ID number of a user waiting for activation.

    Raises:
        RegistrationError: If the user cannot be found or is already
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
        RegistrationError: If the user cannot be found or is already
            registered, or the OTP is wrong, expired or no longer valid.
    """
    user = _get_pending_user(id_number)
    otp = _check_otp(user, OTP_PURPOSE_REGISTRATION, code)
    with transaction.atomic():
        otp.save()
        user.mark_active()
        user.save()


# --- Helpers: users and university records ---


def _check_password_length(password: str) -> None:
    """Reject a password shorter than the minimum length.

    Args:
        password: The chosen password in plain text.

    Raises:
        RegistrationError: If the password is too short.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise RegistrationError(MSG_PASSWORD_TOO_SHORT)


def _find_member_and_destination(id_number: str) -> tuple[UniversityMember, str]:
    """Look up the ID in the records and choose where to send the OTP.

    The email is used first; the mobile number only if there is no email.

    Args:
        id_number: The IUB ID number to look up.

    Returns:
        The member from the records and their email or mobile number.

    Raises:
        RegistrationError: If the ID is not in the records or has no
            contact details.
    """
    member = get_records_client().find_member(id_number)
    if member is None:
        raise RegistrationError(MSG_ID_NOT_FOUND)
    destination = member.email or member.mobile
    if not destination:
        raise RegistrationError(MSG_NO_CONTACT_DETAILS)
    return member, destination


def _raise_if_registered(user: User) -> None:
    """Reject a user whose account is no longer waiting for activation.

    Active and locked accounts have both finished registration.

    Args:
        user: The user to check.

    Raises:
        RegistrationError: If the account is not pending activation.
    """
    if user.account_status != ACCOUNT_PENDING_ACTIVATION:
        raise RegistrationError(MSG_ALREADY_REGISTERED)


def _get_or_build_unregistered_user(id_number: str) -> User:
    """Return the pending user for this ID, or a new unsaved user.

    Args:
        id_number: The IUB ID number.

    Returns:
        The existing pending user, or a new user that is not saved yet.

    Raises:
        RegistrationError: If the ID is already registered.
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
        RegistrationError: If no user has this ID, or the ID is already
            registered.
    """
    user = User.objects.filter(username=id_number).first()
    if user is None:
        raise RegistrationError(MSG_ID_NOT_FOUND)
    _raise_if_registered(user)
    return user


# --- Helpers: OTPs (written so FR-04 password reset can reuse them) ---


def _generate_otp_code() -> str:
    """Make a random numeric OTP with the ``secrets`` module.

    Returns:
        A string of ``OTP_LENGTH`` random digits.
    """
    return "".join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


def _check_request_limit(user: User, now: datetime) -> None:
    """Reject the request if the user asked for too many OTPs recently.

    Every OTP row is one request, whatever its purpose or status.

    Args:
        user: The user asking for an OTP.
        now: The current time.

    Raises:
        RegistrationError: If the limit for the time window is reached.
    """
    window_start = now - timedelta(minutes=OTP_REQUEST_WINDOW_MINUTES)
    recent_requests = Otp.objects.filter(user=user, created_at__gt=window_start)
    if recent_requests.count() >= OTP_REQUEST_LIMIT:
        raise RegistrationError(MSG_TOO_MANY_REQUESTS)


def _issue_otp(user: User, destination: str, purpose: str) -> None:
    """Cancel the earlier valid OTP, then create and send a new one.

    Must be called inside ``transaction.atomic()`` so that a failed send
    does not leave a new OTP that the user never received.

    Args:
        user: The saved user who receives the OTP.
        destination: The email address or mobile number.
        purpose: One of the OTP purpose constants.

    Raises:
        RegistrationError: If too many OTPs were requested.
    """
    now = timezone.now()
    _check_request_limit(user, now)
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

    Rejections are saved straight away (expired status, wrong-attempt
    count) so they still count after the error is raised. On success the
    OTP is marked used but NOT saved, so the caller can save it together
    with its own changes.

    Args:
        user: The user who typed the OTP.
        purpose: One of the OTP purpose constants.
        code: The OTP typed by the user.

    Returns:
        The matching OTP, marked used but not saved.

    Raises:
        RegistrationError: If there is no valid OTP, or the OTP is expired
            or wrong.
    """
    otp = Otp.objects.filter(user=user, purpose=purpose, status=OTP_VALID).first()
    if otp is None:
        raise RegistrationError(MSG_OTP_NO_LONGER_VALID)
    if otp.is_expired(timezone.now()):
        otp.status = OTP_EXPIRED
        otp.save()
        raise RegistrationError(MSG_OTP_EXPIRED)
    # check_password compares hashes in constant time.
    if not check_password(code, otp.code_hash):
        raise RegistrationError(_record_wrong_attempt(otp))
    otp.status = OTP_USED
    return otp


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
