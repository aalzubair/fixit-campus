"""Tests for the FR-04 password-reset rules in services.py.

Acceptance criteria (AC) numbers refer to SRS FR-04 Confirmation 1 to 11.
"""

from datetime import timedelta
from unittest import mock

from django.db import DatabaseError

from campus.constants import (
    MSG_ACCOUNT_LOCKED,
    MSG_INVALID_LOGIN,
    MSG_OTP_EXPIRED,
    MSG_OTP_INCORRECT,
    MSG_OTP_NO_LONGER_VALID,
    MSG_PASSWORD_TOO_SHORT,
    MSG_TOO_MANY_REQUESTS,
    OTP_INVALID,
    OTP_LIFETIME_MINUTES,
    OTP_PURPOSE_PASSWORD_RESET,
    OTP_PURPOSE_REGISTRATION,
    OTP_REQUEST_LIMIT,
    OTP_USED,
    OTP_VALID,
    PASSWORD_MIN_LENGTH,
)
from campus.models import Otp, User
from campus.services import (
    ServiceError,
    log_in_user,
    register_user,
    request_new_registration_otp,
    request_password_reset,
    reset_password,
)
from campus.tests.base import (
    FACULTY_ID,
    GOOD_PASSWORD,
    MOBILE_ONLY_ID,
    NEW_PASSWORD,
    STAFF_MOBILE,
    START_TIME,
    STUDENT_EMAIL,
    STUDENT_ID,
    UNKNOWN_ID,
    RegistrationTestCase,
)
from campus.tests.fakes import FailingOtpSender

ONE_SECOND = timedelta(seconds=1)
FIRST_CODE = "111111"
SECOND_CODE = "222222"


def reset_otps(id_number: str) -> list[Otp]:
    """Return the password-reset OTPs of a user, newest first.

    Args:
        id_number: The IUB ID number of the user.

    Returns:
        The password-reset OTP rows.
    """
    return list(
        Otp.objects.filter(user__username=id_number, purpose=OTP_PURPOSE_PASSWORD_RESET)
    )


class ResetTestCase(RegistrationTestCase):
    """Base class: an active student who has not asked for a reset yet."""

    def setUp(self) -> None:
        """Create an active student and remember how many OTPs were sent."""
        super().setUp()
        self.make_active_user(STUDENT_ID)
        self.sent_before = len(self.sender.sent_messages)

    def assert_nothing_sent(self) -> None:
        """Check that no OTP was sent after setUp."""
        self.assertEqual(len(self.sender.sent_messages), self.sent_before)


class RequestPasswordResetTests(ResetTestCase):
    """request_password_reset: who gets an OTP and who does not."""

    def test_reset_sends_otp_to_email(self) -> None:
        """AC 1: the OTP goes to the registered email."""
        request_password_reset(STUDENT_ID)
        self.assertEqual(self.sender.last_destination, STUDENT_EMAIL)
        self.assertEqual(len(reset_otps(STUDENT_ID)), 1)

    def test_reset_sends_otp_to_mobile_when_no_email(self) -> None:
        """AC 1: without an email the OTP goes to the mobile number."""
        self.make_active_user(MOBILE_ONLY_ID)
        request_password_reset(MOBILE_ONLY_ID)
        self.assertEqual(self.sender.last_destination, STAFF_MOBILE)

    def test_otp_is_stored_only_as_hash(self) -> None:
        """The plain reset OTP is never stored."""
        request_password_reset(STUDENT_ID)
        self.assertNotEqual(reset_otps(STUDENT_ID)[0].code_hash, self.sender.last_code)

    def test_unknown_id_sends_nothing_and_raises_nothing(self) -> None:
        """AC 8: an unknown ID gets no OTP and no error."""
        request_password_reset(UNKNOWN_ID)
        self.assert_nothing_sent()

    def test_empty_id_sends_nothing(self) -> None:
        """An empty ID is treated like an unknown ID."""
        request_password_reset("")
        self.assert_nothing_sent()

    def test_pending_id_sends_nothing(self) -> None:
        """An account that is not activated gets no reset OTP."""
        register_user(FACULTY_ID, GOOD_PASSWORD)
        sent_after_register = len(self.sender.sent_messages)
        request_password_reset(FACULTY_ID)
        self.assertEqual(len(self.sender.sent_messages), sent_after_register)
        self.assertEqual(reset_otps(FACULTY_ID), [])

    def test_member_no_longer_in_records_gets_no_otp(self) -> None:
        """AC 8: a member who left the university gets no OTP and no error."""
        self.records.remove_member(STUDENT_ID)
        request_password_reset(STUDENT_ID)
        self.assert_nothing_sent()

    def test_member_without_contact_details_gets_no_otp(self) -> None:
        """Contact details removed from the records: nothing to send to."""
        self.records.change_member(STUDENT_ID, email=None, mobile=None)
        request_password_reset(STUDENT_ID)
        self.assert_nothing_sent()

    def test_locked_account_is_rejected(self) -> None:
        """AC 11: a locked account cannot ask for a reset."""
        self.type_wrong_passwords(STUDENT_ID)
        with self.assertRaisesMessage(ServiceError, MSG_ACCOUNT_LOCKED):
            request_password_reset(STUDENT_ID)
        self.assert_nothing_sent()

    def test_new_otp_cancels_earlier_otp(self) -> None:
        """AC 6: a new request makes the earlier OTP invalid at once."""
        self.start_patch("campus.services._generate_otp_code", FIRST_CODE)
        request_password_reset(STUDENT_ID)
        self.start_patch("campus.services._generate_otp_code", SECOND_CODE)
        request_password_reset(STUDENT_ID)
        newest, earlier = reset_otps(STUDENT_ID)
        self.assertEqual(newest.status, OTP_VALID)
        self.assertEqual(earlier.status, OTP_INVALID)
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            reset_password(STUDENT_ID, FIRST_CODE, NEW_PASSWORD)
        reset_password(STUDENT_ID, SECOND_CODE, NEW_PASSWORD)

    def test_failed_delivery_stores_no_otp(self) -> None:
        """Delivery failure behaves as in FR-01: the error passes, no OTP stays."""
        self.start_patch("campus.services.get_otp_sender", FailingOtpSender())
        with self.assertRaises(ConnectionError):
            request_password_reset(STUDENT_ID)
        self.assertEqual(reset_otps(STUDENT_ID), [])

    def test_failed_new_otp_delivery_keeps_previous_otp_valid(self) -> None:
        """The earlier OTP is cancelled only if the new one was sent."""
        request_password_reset(STUDENT_ID)
        code = self.sender.last_code
        self.start_patch("campus.services.get_otp_sender", FailingOtpSender())
        with self.assertRaises(ConnectionError):
            request_password_reset(STUDENT_ID)
        reset_password(STUDENT_ID, code, NEW_PASSWORD)


class RequestLimitTests(ResetTestCase):
    """At most 5 OTP requests in 15 minutes, counted per purpose."""

    def test_fifth_request_in_window_is_accepted(self) -> None:
        """Boundary: the 5th request is still allowed."""
        for _ in range(OTP_REQUEST_LIMIT):
            request_password_reset(STUDENT_ID)
        self.assertEqual(len(reset_otps(STUDENT_ID)), OTP_REQUEST_LIMIT)

    def test_sixth_request_in_window_is_rejected(self) -> None:
        """AC 10: the 6th request in 15 minutes is rejected."""
        for _ in range(OTP_REQUEST_LIMIT):
            request_password_reset(STUDENT_ID)
        with self.assertRaisesMessage(ServiceError, MSG_TOO_MANY_REQUESTS):
            request_password_reset(STUDENT_ID)
        self.assertEqual(len(reset_otps(STUDENT_ID)), OTP_REQUEST_LIMIT)

    def test_registration_otps_do_not_count_against_reset_limit(self) -> None:
        """Per purpose: the registration OTP from setUp is not counted."""
        self.assertTrue(Otp.objects.filter(purpose=OTP_PURPOSE_REGISTRATION).exists())
        for _ in range(OTP_REQUEST_LIMIT):
            request_password_reset(STUDENT_ID)
        self.assertEqual(len(reset_otps(STUDENT_ID)), OTP_REQUEST_LIMIT)

    def test_reset_otps_do_not_count_against_registration_limit(self) -> None:
        """Per purpose: reset OTPs do not use up the registration limit."""
        register_user(FACULTY_ID, GOOD_PASSWORD)
        pending_user = User.objects.get(username=FACULTY_ID)
        # A pending user cannot ask for a reset, so the rows are made directly.
        for _ in range(OTP_REQUEST_LIMIT):
            Otp.objects.create(
                user=pending_user,
                purpose=OTP_PURPOSE_PASSWORD_RESET,
                code_hash="unused",
                status=OTP_INVALID,
                created_at=START_TIME,
                expires_at=START_TIME,
            )
        for _ in range(OTP_REQUEST_LIMIT - 1):
            request_new_registration_otp(FACULTY_ID)
        registration_otps = Otp.objects.filter(
            user=pending_user, purpose=OTP_PURPOSE_REGISTRATION
        )
        self.assertEqual(registration_otps.count(), OTP_REQUEST_LIMIT)


class ResetPasswordTests(ResetTestCase):
    """reset_password: the OTP and the new password."""

    def setUp(self) -> None:
        """Ask for a reset OTP."""
        super().setUp()
        request_password_reset(STUDENT_ID)

    def stored_user(self) -> User:
        """Read the student fresh from the database.

        Returns:
            The stored student user.
        """
        return User.objects.get(username=STUDENT_ID)

    def test_correct_otp_changes_password(self) -> None:
        """AC 2: the new password works for login."""
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        self.assertEqual(log_in_user(STUDENT_ID, NEW_PASSWORD).username, STUDENT_ID)

    def test_correct_otp_is_marked_used(self) -> None:
        """A used OTP cannot change the password a second time."""
        code = self.sender.last_code
        reset_password(STUDENT_ID, code, NEW_PASSWORD)
        self.assertEqual(reset_otps(STUDENT_ID)[0].status, OTP_USED)
        with self.assertRaises(ServiceError):
            reset_password(STUDENT_ID, code, GOOD_PASSWORD)

    def test_old_password_is_rejected_after_reset(self) -> None:
        """AC 7: the old password no longer works."""
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        with self.assertRaisesMessage(ServiceError, MSG_INVALID_LOGIN):
            log_in_user(STUDENT_ID, GOOD_PASSWORD)

    def test_new_password_is_stored_as_hash(self) -> None:
        """The new password is stored only as a salted hash."""
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        self.assertNotIn(NEW_PASSWORD, self.stored_user().password)

    def test_failed_password_save_keeps_otp_valid(self) -> None:
        """Password and OTP are saved in one transaction: all or nothing."""
        with mock.patch.object(User, "save", side_effect=DatabaseError):
            with self.assertRaises(DatabaseError):
                reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        self.assertEqual(reset_otps(STUDENT_ID)[0].status, OTP_VALID)
        self.assertTrue(self.stored_user().check_password(GOOD_PASSWORD))

    def test_seven_character_password_is_rejected(self) -> None:
        """AC 9, boundary: 7 characters is too short."""
        short_password = "x" * (PASSWORD_MIN_LENGTH - 1)
        with self.assertRaisesMessage(ServiceError, MSG_PASSWORD_TOO_SHORT):
            reset_password(STUDENT_ID, self.sender.last_code, short_password)
        self.assertTrue(self.stored_user().check_password(GOOD_PASSWORD))

    def test_short_password_leaves_otp_valid(self) -> None:
        """A too-short password does not use the OTP or count as a wrong try."""
        short_password = "x" * (PASSWORD_MIN_LENGTH - 1)
        with self.assertRaises(ServiceError):
            reset_password(STUDENT_ID, self.sender.last_code, short_password)
        otp = reset_otps(STUDENT_ID)[0]
        self.assertEqual(otp.status, OTP_VALID)
        self.assertEqual(otp.wrong_attempts, 0)
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)

    def test_eight_character_password_is_accepted(self) -> None:
        """Boundary: exactly 8 characters is long enough."""
        eight_characters = "y" * PASSWORD_MIN_LENGTH
        reset_password(STUDENT_ID, self.sender.last_code, eight_characters)
        self.assertTrue(self.stored_user().check_password(eight_characters))

    def test_wrong_otp_is_rejected_and_user_may_retry(self) -> None:
        """AC 3: a wrong OTP is rejected and the correct one still works."""
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            reset_password(STUDENT_ID, self.wrong_code(), NEW_PASSWORD)
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)

    def test_second_wrong_otp_keeps_otp_valid(self) -> None:
        """Boundary: after 2 wrong OTPs the OTP is still valid."""
        for _ in range(2):
            with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
                reset_password(STUDENT_ID, self.wrong_code(), NEW_PASSWORD)
        self.assertEqual(reset_otps(STUDENT_ID)[0].status, OTP_VALID)

    def test_third_wrong_otp_invalidates_otp(self) -> None:
        """AC 4: the 3rd wrong OTP makes the OTP invalid."""
        for _ in range(2):
            with self.assertRaises(ServiceError):
                reset_password(STUDENT_ID, self.wrong_code(), NEW_PASSWORD)
        with self.assertRaisesMessage(ServiceError, MSG_OTP_NO_LONGER_VALID):
            reset_password(STUDENT_ID, self.wrong_code(), NEW_PASSWORD)
        with self.assertRaisesMessage(ServiceError, MSG_OTP_NO_LONGER_VALID):
            reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)

    def test_non_digit_otp_is_rejected_as_incorrect(self) -> None:
        """The service does not crash on a badly shaped code."""
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            reset_password(STUDENT_ID, "abcdef", NEW_PASSWORD)

    def test_otp_is_accepted_at_four_minutes_fifty_nine(self) -> None:
        """Boundary: just before expiry the OTP works."""
        self.move_clock(timedelta(minutes=OTP_LIFETIME_MINUTES) - ONE_SECOND)
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)

    def test_otp_is_rejected_at_five_minutes_one_second(self) -> None:
        """AC 5, boundary: just after expiry the OTP is rejected."""
        self.move_clock(timedelta(minutes=OTP_LIFETIME_MINUTES) + ONE_SECOND)
        with self.assertRaisesMessage(ServiceError, MSG_OTP_EXPIRED):
            reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)

    def test_new_otp_can_be_requested_after_expiry(self) -> None:
        """AC 5: after expiry a new OTP can be requested and works."""
        self.move_clock(timedelta(minutes=OTP_LIFETIME_MINUTES) + ONE_SECOND)
        with self.assertRaises(ServiceError):
            reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        request_password_reset(STUDENT_ID)
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)

    def test_unknown_id_gets_incorrect_otp_message(self) -> None:
        """The verify step does not reveal whether an ID exists."""
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            reset_password(UNKNOWN_ID, self.sender.last_code, NEW_PASSWORD)

    def test_reset_does_not_unlock_account(self) -> None:
        """Assumption: changing the password leaves the lock in place."""
        code = self.sender.last_code
        self.type_wrong_passwords(STUDENT_ID)
        reset_password(STUDENT_ID, code, NEW_PASSWORD)
        with self.assertRaisesMessage(ServiceError, MSG_ACCOUNT_LOCKED):
            log_in_user(STUDENT_ID, NEW_PASSWORD)
