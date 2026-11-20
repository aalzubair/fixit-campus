"""Database tables for FixIt Campus: user accounts and one-time passwords."""

from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models

from campus.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_PENDING_ACTIVATION,
    ACCOUNT_STATUS_CHOICES,
    ACCOUNT_STATUS_MAX_LENGTH,
    OTP_HASH_MAX_LENGTH,
    OTP_PURPOSE_CHOICES,
    OTP_PURPOSE_MAX_LENGTH,
    OTP_STATUS_CHOICES,
    OTP_STATUS_MAX_LENGTH,
    OTP_VALID,
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
