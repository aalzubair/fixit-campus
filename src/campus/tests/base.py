"""Shared test setup for FR-01: fake outside systems, a fixed clock, fast hashing."""

from datetime import UTC, datetime, timedelta
from unittest import mock

from django.test import TestCase, override_settings

from campus.constants import (
    OTP_LENGTH,
    ROLE_ADMINISTRATOR,
    ROLE_FACULTY,
    ROLE_MAINTENANCE_STAFF,
    ROLE_STUDENT,
    ROLE_SUPERVISOR,
)
from campus.models import User
from campus.records import UniversityMember
from campus.services import register_user, verify_registration_otp
from campus.tests.fakes import FakeOtpSender, FakeRecordsClient

# MD5 is unsafe for real passwords but makes the test suite fast.
FAST_PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
START_TIME = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)

STUDENT_ID = "1000001"
FACULTY_ID = "1000002"
MOBILE_ONLY_ID = "1000003"
SUPERVISOR_ID = "1000004"
ADMINISTRATOR_ID = "1000005"
NO_CONTACT_ID = "1000006"
UNKNOWN_ID = "9999999"
STUDENT_EMAIL = "student@test.example"
STAFF_MOBILE = "+8800000000003"

GOOD_PASSWORD = "first-pass-1"
NEW_PASSWORD = "second-pass-2"

TEST_MEMBERS = (
    UniversityMember(STUDENT_ID, ROLE_STUDENT, STUDENT_EMAIL, "+8800000000001"),
    UniversityMember(FACULTY_ID, ROLE_FACULTY, "faculty@test.example", None),
    UniversityMember(MOBILE_ONLY_ID, ROLE_MAINTENANCE_STAFF, None, STAFF_MOBILE),
    UniversityMember(SUPERVISOR_ID, ROLE_SUPERVISOR, "boss@test.example", None),
    UniversityMember(ADMINISTRATOR_ID, ROLE_ADMINISTRATOR, "admin@test.example", None),
    UniversityMember(NO_CONTACT_ID, ROLE_STUDENT, None, None),
)


@override_settings(PASSWORD_HASHERS=FAST_PASSWORD_HASHERS)
class RegistrationTestCase(TestCase):
    """Base class: services use fakes and the clock starts at START_TIME."""

    def setUp(self) -> None:
        """Replace the outside systems and the clock for each test."""
        super().setUp()
        self.sender = FakeOtpSender()
        self.clock = self.start_patch("django.utils.timezone.now", START_TIME)
        self.start_patch("campus.services.get_otp_sender", self.sender)
        self.start_patch(
            "campus.services.get_records_client", FakeRecordsClient(TEST_MEMBERS)
        )

    def start_patch(self, target: str, return_value: object) -> mock.MagicMock:
        """Patch a function for this test only.

        Args:
            target: Dotted path of the function to replace.
            return_value: What the replacement returns.

        Returns:
            The mock that replaces the function.
        """
        patcher = mock.patch(target, return_value=return_value)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def move_clock(self, delta: timedelta) -> None:
        """Set the clock to START_TIME plus a time difference.

        Args:
            delta: How long after START_TIME it now is.
        """
        self.clock.return_value = START_TIME + delta

    def wrong_code(self) -> str:
        """Make a code that is different from the last OTP sent.

        Returns:
            A well-formed but wrong OTP.
        """
        wrong_number = (int(self.sender.last_code) + 1) % 10**OTP_LENGTH
        return str(wrong_number).zfill(OTP_LENGTH)

    def make_active_user(self, id_number: str) -> User:
        """Register a user and activate the account with the correct OTP.

        Args:
            id_number: An IUB ID number from TEST_MEMBERS.

        Returns:
            The active user.
        """
        register_user(id_number, GOOD_PASSWORD)
        verify_registration_otp(id_number, self.sender.last_code)
        return User.objects.get(username=id_number)
