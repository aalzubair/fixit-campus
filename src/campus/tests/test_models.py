"""Tests for the small helpers in models.py."""

from datetime import timedelta

from django.test import SimpleTestCase

from campus.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_PENDING_ACTIVATION,
    OTP_PURPOSE_REGISTRATION,
    OTP_VALID,
)
from campus.models import Otp, User
from campus.tests.base import START_TIME, STUDENT_ID


class UserHelperTests(SimpleTestCase):
    """User.mark_pending, User.mark_active and __str__."""

    def test_mark_pending_blocks_login(self) -> None:
        """A pending account is not active for Django's authentication."""
        user = User(username=STUDENT_ID)
        user.mark_pending()
        self.assertEqual(user.account_status, ACCOUNT_PENDING_ACTIVATION)
        self.assertFalse(user.is_active)

    def test_mark_active_allows_login(self) -> None:
        """An activated account is active for Django's authentication."""
        user = User(username=STUDENT_ID)
        user.mark_pending()
        user.mark_active()
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)
        self.assertTrue(user.is_active)

    def test_str_is_id_number(self) -> None:
        """A user is shown by IUB ID number."""
        self.assertEqual(str(User(username=STUDENT_ID)), STUDENT_ID)


class OtpHelperTests(SimpleTestCase):
    """Otp.is_expired and __str__."""

    def setUp(self) -> None:
        """Make an unsaved OTP that expires at START_TIME."""
        self.otp = Otp(
            purpose=OTP_PURPOSE_REGISTRATION,
            code_hash="hash",
            created_at=START_TIME - timedelta(minutes=5),
            expires_at=START_TIME,
        )

    def test_not_expired_before_expiry_time(self) -> None:
        """Boundary: one second before expiry the OTP still works."""
        self.assertFalse(self.otp.is_expired(START_TIME - timedelta(seconds=1)))

    def test_not_expired_at_exact_expiry_time(self) -> None:
        """Boundary: exactly 5 minutes still counts as within 5 minutes."""
        self.assertFalse(self.otp.is_expired(START_TIME))

    def test_expired_after_expiry_time(self) -> None:
        """Boundary: one second after expiry the OTP is expired."""
        self.assertTrue(self.otp.is_expired(START_TIME + timedelta(seconds=1)))

    def test_str_does_not_show_code_hash(self) -> None:
        """The text form shows purpose and status, never the hash."""
        text = str(self.otp)
        self.assertIn(OTP_PURPOSE_REGISTRATION, text)
        self.assertIn(OTP_VALID, text)
        self.assertNotIn(self.otp.code_hash, text)
