"""Database tables for FixIt Campus: users, one-time passwords and complaints."""

from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models

from campus.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_PENDING_ACTIVATION,
    ACCOUNT_STATUS_CHOICES,
    ACCOUNT_STATUS_MAX_LENGTH,
    CATEGORY_CHOICES,
    CATEGORY_MAX_LENGTH,
    COMPLAINT_ID_MAX_LENGTH,
    COMPLAINT_OPEN,
    COMPLAINT_PHOTO_DIR,
    COMPLAINT_STATUS_CHOICES,
    COMPLAINT_STATUS_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    LOCATION_PART_MAX_LENGTH,
    OTP_HASH_MAX_LENGTH,
    OTP_PURPOSE_CHOICES,
    OTP_PURPOSE_MAX_LENGTH,
    OTP_STATUS_CHOICES,
    OTP_STATUS_MAX_LENGTH,
    OTP_VALID,
    REASON_MAX_LENGTH,
    ROLE_CHOICES,
    ROLE_MAX_LENGTH,
)


class User(AbstractUser):
    """A university member who has started or finished registration.

    The inherited ``username`` field stores the IUB ID number, so Django's
    login system works with the ID number without extra code. The inherited
    ``password`` field stores a salted hash made by Django.
    """

    role = models.CharField(max_length=ROLE_MAX_LENGTH, choices=ROLE_CHOICES)
    account_status = models.CharField(
        max_length=ACCOUNT_STATUS_MAX_LENGTH,
        choices=ACCOUNT_STATUS_CHOICES,
        default=ACCOUNT_PENDING_ACTIVATION,
    )
    # Wrong passwords in a row since the last successful login (FR-02).
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    # The account is locked while this time is in the future (FR-02).
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        """Return the IUB ID number.

        Returns:
            The IUB ID number of this user.
        """
        return self.username

    def mark_pending(self) -> None:
        """Set the account to pending activation (does not save).

        ``is_active`` is False so Django's authentication rejects the
        account until the OTP is verified.
        """
        self.account_status = ACCOUNT_PENDING_ACTIVATION
        self.is_active = False

    def mark_active(self) -> None:
        """Set the account to active so the user can log in (does not save)."""
        self.account_status = ACCOUNT_ACTIVE
        self.is_active = True

    def is_locked(self, now: datetime) -> bool:
        """Tell whether the account is locked at the given time.

        Args:
            now: The current time.

        Returns:
            True if ``locked_until`` is set and later than ``now``.
        """
        return self.locked_until is not None and self.locked_until > now

    def clear_lock(self) -> None:
        """Remove the lock and start counting wrong passwords from 0 (does not save)."""
        self.failed_login_attempts = 0
        self.locked_until = None


class Otp(models.Model):
    """A one-time password sent to a user for one purpose.

    Only a hash of the code is stored, never the plain code. Each row is
    also one OTP request, which is how the request limit is counted.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    purpose = models.CharField(
        max_length=OTP_PURPOSE_MAX_LENGTH, choices=OTP_PURPOSE_CHOICES
    )
    code_hash = models.CharField(max_length=OTP_HASH_MAX_LENGTH)
    status = models.CharField(
        max_length=OTP_STATUS_MAX_LENGTH, choices=OTP_STATUS_CHOICES, default=OTP_VALID
    )
    wrong_attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    class Meta:
        """Show the newest OTP first.

        ``-id`` breaks ties when two OTPs share the same ``created_at``.
        """

        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        """Return a short description without the code.

        Returns:
            The purpose and status of this OTP.
        """
        return f"{self.purpose} OTP ({self.status})"

    def is_expired(self, now: datetime) -> bool:
        """Tell whether the OTP is past its expiry time.

        Args:
            now: The current time.

        Returns:
            True if ``now`` is later than ``expires_at``.
        """
        return now > self.expires_at


class Complaint(models.Model):
    """A maintenance complaint submitted by a complainant (FR-06).

    Besides the fields F3 and F4 use, it holds the fields that the staff and
    supervisor features need (assignment, resolution, rejection), so that
    every feature shares one table and one migration history.
    """

    complaint_id = models.CharField(
        max_length=COMPLAINT_ID_MAX_LENGTH, unique=True, editable=False
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="submitted_complaints"
    )
    category = models.CharField(
        max_length=CATEGORY_MAX_LENGTH, choices=CATEGORY_CHOICES
    )
    # The three parts of a location (FR-14 location rule). A place without a
    # floor, such as a lift, keeps ``floor`` empty.
    building = models.CharField(max_length=LOCATION_PART_MAX_LENGTH)
    floor = models.CharField(max_length=LOCATION_PART_MAX_LENGTH, blank=True)
    room_or_area = models.CharField(max_length=LOCATION_PART_MAX_LENGTH)
    description = models.TextField(max_length=DESCRIPTION_MAX_LENGTH, blank=True)
    photo = models.FileField(upload_to=COMPLAINT_PHOTO_DIR, blank=True)
    is_safety_hazard = models.BooleanField(default=False)
    status = models.CharField(
        max_length=COMPLAINT_STATUS_MAX_LENGTH,
        choices=COMPLAINT_STATUS_CHOICES,
        default=COMPLAINT_OPEN,
    )
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_complaints",
    )
    created_at = models.DateTimeField()
    # When the complaint last became Open, by submission or by reopening. The
    # 48-hour overdue rule counts from here (FR-15).
    opened_at = models.DateTimeField()
    # Shown to the user as "Last status change" (FR-09).
    status_changed_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.CharField(max_length=REASON_MAX_LENGTH, blank=True)
    rejection_reason = models.CharField(max_length=REASON_MAX_LENGTH, blank=True)
    rejected_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rejected_complaints",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    followers = models.ManyToManyField(
        User, through="Follow", related_name="followed_complaints"
    )

    class Meta:
        """Show the newest complaint first."""

        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        """Return the complaint ID.

        Returns:
            The unique complaint ID, for example ``CMP-2026-00001``.
        """
        return self.complaint_id

    def location_label(self) -> str:
        """Join the parts of the location into one line.

        Returns:
            For example ``"Block A, 3rd floor, Room 302"``. An empty floor
            is left out.
        """
        parts = (self.building, self.floor, self.room_or_area)
        return ", ".join(part for part in parts if part)


class Follow(models.Model):
    """A user follows a complaint of another user instead of duplicating it.

    The follower is told when the complaint is Resolved or Rejected (FR-07).
    Sending that notification belongs to FR-05, FR-13 and FR-20.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    created_at = models.DateTimeField()

    class Meta:
        """A user can follow the same complaint only once."""

        constraints = (
            models.UniqueConstraint(
                fields=("user", "complaint"), name="unique_follow_per_user"
            ),
        )

    def __str__(self) -> str:
        """Return who follows which complaint.

        Returns:
            The IUB ID number and the complaint ID.
        """
        return f"{self.user} follows {self.complaint}"
