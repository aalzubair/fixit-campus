"""Business rules for FixIt Campus (Application layer).

This module holds the rules for FR-01 (register with OTP verification),
FR-02 (log in, account lock, IUB records check), FR-04 (reset password),
FR-06 to FR-08 (submit a complaint, find similar ones, follow), FR-09 (track
complaints), FR-10 (reopen) and FR-21 (browse complaints). FR-03 (log out,
idle timeout) only changes the session, so it lives in the Presentation layer.
This module never sees the request, the session or HTML.
Outside systems are used only through ``records.py`` (university records)
and ``delivery.py`` (sending the OTP).
"""

import secrets
import string
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import PurePath

from django.contrib.auth.hashers import check_password, make_password
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models.fields.files import FieldFile
from django.utils import timezone

from campus.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_LOCK_MINUTES,
    ACCOUNT_PENDING_ACTIVATION,
    BROWSABLE_STATUSES,
    COMPLAINT_ID_NUMBER_WIDTH,
    COMPLAINT_ID_PREFIX_FORMAT,
    COMPLAINT_OPEN,
    COMPLAINT_RESOLVED,
    LOGIN_MAX_FAILED_ATTEMPTS,
    MSG_ACCOUNT_LOCKED,
    MSG_ACCOUNT_NO_LONGER_ACTIVE,
    MSG_ALREADY_REGISTERED,
    MSG_CANNOT_FOLLOW_OWN,
    MSG_COMPLAINT_NOT_ALLOWED,
    MSG_ID_NOT_FOUND,
    MSG_INVALID_LOGIN,
    MSG_NO_CONTACT_DETAILS,
    MSG_ONLY_BROWSABLE_CAN_FOLLOW,
    MSG_ONLY_RESOLVED_CAN_REOPEN,
    MSG_OTP_EXPIRED,
    MSG_OTP_INCORRECT,
    MSG_OTP_NO_LONGER_VALID,
    MSG_PASSWORD_TOO_SHORT,
    MSG_REOPEN_EXPIRED,
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
    REOPEN_WINDOW_DAYS,
)
from campus.delivery import get_otp_sender
from campus.models import Complaint, Follow, Otp, User
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


@dataclass(frozen=True)
class ComplaintDraft:
    """The checked input of the complaint form (FR-06).

    Attributes:
        category: A category value from ``CATEGORY_CHOICES``.
        building: The building of the location.
        floor: The floor, or an empty string for a place without a floor.
        room_or_area: The room or area of the location.
        description: A short description, may be empty.
        photo: The uploaded photo, or None.
        is_safety_hazard: True if the user ticked the Safety Hazard box (FR-08).
    """

    category: str
    building: str
    floor: str
    room_or_area: str
    description: str
    photo: UploadedFile | None
    is_safety_hazard: bool


@dataclass(frozen=True)
class BrowseFilters:
    """The filters of Existing Complaints (FR-21); an empty value means "all"."""

    building: str = ""
    category: str = ""
    status: str = ""


@dataclass(frozen=True)
class ComplaintSummary:
    """The only facts of a complaint that other users may see (FR-07, FR-21).

    It holds category, location, status and dates. Reporter name, description
    and photo are left out here, so no page can show them by mistake.
    """

    complaint_id: str
    category: str
    location: str
    status: str
    status_label: str
    created_at: datetime
    status_changed_at: datetime


@dataclass(frozen=True)
class ListedComplaint:
    """One row of a complaint list: the summary and how the user relates to it.

    Attributes:
        summary: What the user may see of the complaint.
        is_following: True if the user follows the complaint.
        is_own: True if the user submitted the complaint.
    """

    summary: ComplaintSummary
    is_following: bool
    is_own: bool


@dataclass(frozen=True)
class MyComplaints:
    """The two lists of the My Complaints page (FR-09).

    Attributes:
        own: Complaints the user submitted, newest status change first.
        following: Complaints of other users that the user follows.
    """

    own: list[Complaint]
    following: list[ListedComplaint]


@dataclass(frozen=True)
class ComplaintDetail:
    """A user's own complaint and what they may do with it (FR-09, FR-10).

    Attributes:
        complaint: The complaint.
        can_reopen: True if it is Resolved and still inside the 7-day window.
        reopen_expired: True if it is Resolved but the window has passed.
        reopen_deadline: The last moment it can be reopened, or None if it
            is not Resolved.
    """

    complaint: Complaint
    can_reopen: bool
    reopen_expired: bool
    reopen_deadline: datetime | None


# --- Public service functions (called by views) ---


def register_user(id_number: str, password: str) -> None:
    """Register a university member and send them an OTP (FR-01).

    A new user is created as pending activation. If the user is already
    pending, the earlier password is replaced and a new OTP is sent.

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
        The user, with the role copied from the records and the
        wrong-password count cleared.

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
    # The records are the source of truth: a changed role takes effect now.
    user.role = member.role
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


def submit_complaint(user: User, draft: ComplaintDraft) -> Complaint:
    """Save a new Open complaint with a unique ID (FR-06).

    The complaint is saved in one transaction, so a failure leaves nothing
    half saved (NFR-10).

    Args:
        user: The logged-in complainant.
        draft: The checked form input.

    Returns:
        The saved complaint.
    """
    now = timezone.now()
    with transaction.atomic():
        complaint_id = _next_complaint_id(now)
        if draft.photo is not None:
            # Store the photo under the complaint ID, not the user's file name.
            draft.photo.name = complaint_id + PurePath(draft.photo.name).suffix.lower()
        complaint = Complaint.objects.create(
            complaint_id=complaint_id,
            submitted_by=user,
            category=draft.category,
            building=draft.building,
            floor=draft.floor,
            room_or_area=draft.room_or_area,
            description=draft.description,
            photo=draft.photo or "",
            is_safety_hazard=draft.is_safety_hazard,
            status=COMPLAINT_OPEN,
            created_at=now,
            opened_at=now,
            status_changed_at=now,
        )
    # HOOK (FR-08, needs FR-05): when ``complaint.is_safety_hazard`` is True,
    # notify maintenance staff and supervisors here, once the notification
    # feature exists. Until then the flag is only saved and shown.
    return complaint


def get_similar_complaints(
    user: User, category: str, building: str, floor: str, room_or_area: str
) -> list[ListedComplaint]:
    """Find Open or In Progress complaints of the same category and place (FR-07).

    Args:
        user: The logged-in complainant, used to mark followed complaints.
        category: A category value.
        building: The building.
        floor: The floor, or an empty string.
        room_or_area: The room or area.

    Returns:
        The matching complaints, newest first, without private details.
    """
    complaints = Complaint.objects.filter(
        status__in=BROWSABLE_STATUSES,
        category=category,
        building=building,
        floor=floor,
        room_or_area=room_or_area,
    )
    return _to_listed(user, complaints)


def browse_complaints(user: User, filters: BrowseFilters) -> list[ListedComplaint]:
    """List Open and In Progress complaints, narrowed by filters (FR-21).

    Args:
        user: The logged-in complainant, used to mark followed complaints.
        filters: Building, category and status; empty means "all".

    Returns:
        The matching complaints, newest first, without private details.
    """
    complaints = Complaint.objects.filter(status__in=BROWSABLE_STATUSES)
    if filters.building:
        complaints = complaints.filter(building=filters.building)
    if filters.category:
        complaints = complaints.filter(category=filters.category)
    if filters.status:
        complaints = complaints.filter(status=filters.status)
    return _to_listed(user, complaints)


def follow_complaint(user: User, complaint_id: str) -> None:
    """Follow another user's Open or In Progress complaint (FR-07).

    Following a complaint that is already followed changes nothing.

    Args:
        user: The logged-in complainant.
        complaint_id: The complaint ID, for example ``CMP-2026-00001``.

    Raises:
        ServiceError: If the complaint does not exist, is the user's own, or
            is not Open or In Progress.
    """
    complaint = Complaint.objects.filter(complaint_id=complaint_id).first()
    if complaint is None:
        raise ServiceError(MSG_COMPLAINT_NOT_ALLOWED)
    if complaint.submitted_by_id == user.pk:
        raise ServiceError(MSG_CANNOT_FOLLOW_OWN)
    if complaint.status not in BROWSABLE_STATUSES:
        raise ServiceError(MSG_ONLY_BROWSABLE_CAN_FOLLOW)
    Follow.objects.get_or_create(
        user=user, complaint=complaint, defaults={"created_at": timezone.now()}
    )


def unfollow_complaint(user: User, complaint_id: str) -> None:
    """Stop following a complaint; nothing happens if it was not followed.

    Args:
        user: The logged-in complainant.
        complaint_id: The complaint ID.
    """
    Follow.objects.filter(user=user, complaint__complaint_id=complaint_id).delete()


def list_my_complaints(user: User) -> MyComplaints:
    """Collect the complaints a user submitted and the ones they follow (FR-09).

    Args:
        user: The logged-in complainant.

    Returns:
        The two lists, each with the newest status change first.
    """
    own = user.submitted_complaints.order_by("-status_changed_at", "-id")
    following = user.followed_complaints.order_by("-status_changed_at", "-id")
    return MyComplaints(own=list(own), following=_to_listed(user, following))


def get_complaint_detail(user: User, complaint_id: str) -> ComplaintDetail:
    """Open one of the user's own complaints (FR-09).

    Args:
        user: The logged-in complainant.
        complaint_id: The complaint ID.

    Returns:
        The complaint and whether it can still be reopened.

    Raises:
        ServiceError: If the complaint does not exist or is not the user's.
    """
    complaint = _get_own_complaint(user, complaint_id)
    deadline = _reopen_deadline(complaint)
    now = timezone.now()
    return ComplaintDetail(
        complaint=complaint,
        can_reopen=deadline is not None and now <= deadline,
        reopen_expired=deadline is not None and now > deadline,
        reopen_deadline=deadline,
    )


def get_complaint_photo(user: User, complaint_id: str) -> FieldFile | None:
    """Return the photo of one of the user's own complaints (NFR-05).

    Photos are only given out here, after the owner check, never by a public
    media URL.

    Args:
        user: The logged-in complainant.
        complaint_id: The complaint ID.

    Returns:
        The stored photo, or None if the complaint has no photo.

    Raises:
        ServiceError: If the complaint does not exist or is not the user's.
    """
    complaint = _get_own_complaint(user, complaint_id)
    return complaint.photo if complaint.photo else None


def reopen_complaint(user: User, complaint_id: str, reason: str) -> None:
    """Reopen a Resolved complaint within 7 days of being resolved (FR-10).

    The complaint goes back to Open, the previous assignment is cleared and
    the reason is saved for maintenance staff and supervisors.

    Args:
        user: The logged-in complainant.
        complaint_id: The complaint ID.
        reason: The checked, non-empty reason.

    Raises:
        ServiceError: If the complaint is not the user's, is not Resolved, or
            was resolved more than 7 days ago.
    """
    now = timezone.now()
    with transaction.atomic():
        complaint = _get_own_complaint(user, complaint_id)
        if complaint.status != COMPLAINT_RESOLVED:
            raise ServiceError(MSG_ONLY_RESOLVED_CAN_REOPEN)
        deadline = _reopen_deadline(complaint)
        if deadline is None or now > deadline:
            raise ServiceError(MSG_REOPEN_EXPIRED)
        complaint.status = COMPLAINT_OPEN
        complaint.assigned_to = None
        complaint.reopen_reason = reason
        complaint.opened_at = now
        complaint.status_changed_at = now
        complaint.save()


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


# --- Helpers: complaints ---


def _next_complaint_id(now: datetime) -> str:
    """Build the next complaint ID of the year, such as ``CMP-2026-00007``.

    Call this inside the transaction that saves the complaint. The unique
    column is the final guard against two equal IDs.

    Args:
        now: The current time; its year is part of the ID.

    Returns:
        An ID that no saved complaint has.
    """
    prefix = COMPLAINT_ID_PREFIX_FORMAT.format(year=now.year)
    last_id = (
        Complaint.objects.filter(complaint_id__startswith=prefix)
        .order_by("-complaint_id")
        .values_list("complaint_id", flat=True)
        .first()
    )
    number = int(last_id.removeprefix(prefix)) + 1 if last_id else 1
    return prefix + str(number).zfill(COMPLAINT_ID_NUMBER_WIDTH)


def _get_own_complaint(user: User, complaint_id: str) -> Complaint:
    """Find a complaint that belongs to the user.

    A missing complaint and another user's complaint give the same error, so
    the answer does not reveal which IDs exist (FR-09, NFR-05).

    Args:
        user: The logged-in complainant.
        complaint_id: The complaint ID.

    Returns:
        The complaint.

    Raises:
        ServiceError: If there is no such complaint of this user.
    """
    complaint = Complaint.objects.filter(
        complaint_id=complaint_id, submitted_by=user
    ).first()
    if complaint is None:
        raise ServiceError(MSG_COMPLAINT_NOT_ALLOWED)
    return complaint


def _reopen_deadline(complaint: Complaint) -> datetime | None:
    """Work out the last moment a Resolved complaint can be reopened.

    Args:
        complaint: Any complaint.

    Returns:
        Seven days after it was resolved, or None if it is not Resolved.
    """
    if complaint.status != COMPLAINT_RESOLVED or complaint.resolved_at is None:
        return None
    return complaint.resolved_at + timedelta(days=REOPEN_WINDOW_DAYS)


def _to_listed(user: User, complaints: Iterable[Complaint]) -> list[ListedComplaint]:
    """Turn complaints into the limited view that other users may see.

    Args:
        user: The logged-in complainant, used for the follow and own marks.
        complaints: The complaints to show.

    Returns:
        One ``ListedComplaint`` per complaint, in the same order.
    """
    followed_ids = set(user.followed_complaints.values_list("pk", flat=True))
    return [
        ListedComplaint(
            summary=ComplaintSummary(
                complaint_id=complaint.complaint_id,
                category=complaint.get_category_display(),
                location=complaint.location_label(),
                status=complaint.status,
                status_label=complaint.get_status_display(),
                created_at=complaint.created_at,
                status_changed_at=complaint.status_changed_at,
            ),
            is_following=complaint.pk in followed_ids,
            is_own=complaint.submitted_by_id == user.pk,
        )
        for complaint in complaints
    ]
