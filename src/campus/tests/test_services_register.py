"""Tests for the FR-01 registration rules in services.py.

Acceptance criteria (AC) numbers refer to SRS FR-01 Confirmation 1 to 12.
"""

from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password

from campus.constants import (
    ACCOUNT_ACTIVE,
    ACCOUNT_LOCK_MINUTES,
    ACCOUNT_PENDING_ACTIVATION,
    MEMBER_NAME_MAX_LENGTH,
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
    OTP_PURPOSE_REGISTRATION,
    OTP_USED,
    OTP_VALID,
    PASSWORD_MIN_LENGTH,
)
from campus.models import Otp, User
from campus.services import (
    ServiceError,
    register_user,
    request_new_registration_otp,
    verify_registration_otp,
)
from campus.tests.base import (
    GOOD_PASSWORD,
    MOBILE_ONLY_ID,
    NEW_PASSWORD,
    NEW_STUDENT_NAME,
    NO_CONTACT_ID,
    STAFF_MOBILE,
    START_TIME,
    STUDENT_EMAIL,
    STUDENT_ID,
    STUDENT_NAME,
    TEST_MEMBERS,
    UNKNOWN_ID,
    RegistrationTestCase,
)
from campus.tests.fakes import FailingOtpSender


def latest_otp(id_number: str) -> Otp:
    """Return the newest OTP of a user, read fresh from the database.

    Args:
        id_number: The IUB ID number of the user.

    Returns:
        The newest OTP row.
    """
    return Otp.objects.filter(user__username=id_number).first()


class RegisterUserTests(RegistrationTestCase):
    """register_user: AC 1, 7, 8, 9, 10 and 12."""

    def test_registration_sends_six_digit_otp_to_email(self) -> None:
        """AC 1: the OTP goes to the email in the records."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertEqual(self.sender.last_destination, STUDENT_EMAIL)
        self.assertEqual(len(self.sender.last_code), OTP_LENGTH)
        self.assertTrue(self.sender.last_code.isdigit())

    def test_registration_sends_otp_to_mobile_when_no_email(self) -> None:
        """AC 1: with no email on record the OTP goes to the mobile number."""
        register_user(MOBILE_ONLY_ID, GOOD_PASSWORD)
        self.assertEqual(self.sender.last_destination, STAFF_MOBILE)

    def test_registration_creates_pending_inactive_user(self) -> None:
        """A new account waits for activation and cannot log in yet."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_PENDING_ACTIVATION)
        self.assertFalse(user.is_active)
        self.assertIsNone(authenticate(username=STUDENT_ID, password=GOOD_PASSWORD))

    def test_password_is_stored_as_hash(self) -> None:
        """The plain password is never stored."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        user = User.objects.get(username=STUDENT_ID)
        self.assertNotEqual(user.password, GOOD_PASSWORD)
        self.assertTrue(user.check_password(GOOD_PASSWORD))

    def test_otp_is_stored_only_as_hash(self) -> None:
        """The plain OTP is never stored; only a matching hash is."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        otp = latest_otp(STUDENT_ID)
        self.assertNotEqual(otp.code_hash, self.sender.last_code)
        self.assertTrue(check_password(self.sender.last_code, otp.code_hash))
        self.assertEqual(otp.purpose, OTP_PURPOSE_REGISTRATION)

    def test_unknown_id_is_rejected(self) -> None:
        """AC 7: an ID that is not in the records is rejected."""
        with self.assertRaisesMessage(ServiceError, MSG_ID_NOT_FOUND):
            register_user(UNKNOWN_ID, GOOD_PASSWORD)
        self.assertFalse(User.objects.exists())
        self.assertEqual(self.sender.sent_messages, [])

    def test_empty_id_is_rejected_as_not_found(self) -> None:
        """An empty ID is not in the records."""
        with self.assertRaisesMessage(ServiceError, MSG_ID_NOT_FOUND):
            register_user("", GOOD_PASSWORD)

    def test_active_id_is_rejected_as_already_registered(self) -> None:
        """AC 8: an activated ID cannot register again."""
        self.make_active_user(STUDENT_ID)
        with self.assertRaisesMessage(ServiceError, MSG_ALREADY_REGISTERED):
            register_user(STUDENT_ID, NEW_PASSWORD)
        user = User.objects.get(username=STUDENT_ID)
        self.assertTrue(user.check_password(GOOD_PASSWORD))

    def test_locked_id_is_rejected_as_already_registered(self) -> None:
        """A locked account has finished registration too."""
        user = self.make_active_user(STUDENT_ID)
        user.locked_until = START_TIME + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
        user.save()
        with self.assertRaisesMessage(ServiceError, MSG_ALREADY_REGISTERED):
            register_user(STUDENT_ID, NEW_PASSWORD)

    def test_seven_character_password_is_rejected(self) -> None:
        """AC 9 boundary: one character below the minimum is rejected."""
        short_password = "a" * (PASSWORD_MIN_LENGTH - 1)
        with self.assertRaisesMessage(ServiceError, MSG_PASSWORD_TOO_SHORT):
            register_user(STUDENT_ID, short_password)
        self.assertFalse(User.objects.exists())

    def test_eight_character_password_is_accepted(self) -> None:
        """AC 9 boundary: exactly the minimum length is accepted."""
        register_user(STUDENT_ID, "a" * PASSWORD_MIN_LENGTH)
        self.assertTrue(User.objects.filter(username=STUDENT_ID).exists())

    def test_empty_password_is_rejected(self) -> None:
        """An empty password is shorter than the minimum."""
        with self.assertRaisesMessage(ServiceError, MSG_PASSWORD_TOO_SHORT):
            register_user(STUDENT_ID, "")

    def test_id_without_contact_details_is_rejected(self) -> None:
        """AC 10: no email and no mobile number means no registration."""
        with self.assertRaisesMessage(ServiceError, MSG_NO_CONTACT_DETAILS):
            register_user(NO_CONTACT_ID, GOOD_PASSWORD)
        self.assertFalse(User.objects.exists())

    def test_registering_again_while_pending_replaces_password(self) -> None:
        """AC 12: the earlier password is replaced by the new one."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        register_user(STUDENT_ID, NEW_PASSWORD)
        user = User.objects.get(username=STUDENT_ID)
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertFalse(user.check_password(GOOD_PASSWORD))

    def test_registering_again_while_pending_sends_new_otp(self) -> None:
        """AC 12: a new OTP is sent and the earlier one is cancelled."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        first_otp = latest_otp(STUDENT_ID)
        register_user(STUDENT_ID, NEW_PASSWORD)
        first_otp.refresh_from_db()
        self.assertEqual(len(self.sender.sent_messages), 2)
        self.assertEqual(first_otp.status, OTP_INVALID)

    def test_failed_delivery_rolls_back_registration(self) -> None:
        """Exception: if the OTP cannot be sent, nothing is saved."""
        self.start_patch("campus.services.get_otp_sender", FailingOtpSender())
        with self.assertRaises(ConnectionError):
            register_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Otp.objects.exists())

    def test_registration_error_keeps_message(self) -> None:
        """ServiceError exposes the message for the view."""
        error = ServiceError(MSG_ID_NOT_FOUND)
        self.assertEqual(error.message, MSG_ID_NOT_FOUND)
        self.assertEqual(str(error), MSG_ID_NOT_FOUND)


class RegisterNameTests(RegistrationTestCase):
    """register_user copies the name from the records into first_name."""

    def stored_name(self) -> str:
        """Read the student's stored first_name fresh from the database.

        Returns:
            The stored first_name of the student.
        """
        return User.objects.get(username=STUDENT_ID).first_name

    def test_name_from_records_is_stored_at_registration(self) -> None:
        """The full name is copied into first_name and last_name stays empty."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.first_name, STUDENT_NAME)
        self.assertEqual(user.last_name, "")
        self.assertEqual(user.get_full_name(), STUDENT_NAME)

    def test_registering_again_while_pending_takes_new_name(self) -> None:
        """A name changed in the records replaces the stored pending name."""
        register_user(STUDENT_ID, GOOD_PASSWORD)
        self.records.change_member(STUDENT_ID, name=NEW_STUDENT_NAME)
        register_user(STUDENT_ID, NEW_PASSWORD)
        self.assertEqual(self.stored_name(), NEW_STUDENT_NAME)

    def test_name_at_length_limit_is_stored_whole(self) -> None:
        """Boundary: a name of exactly the maximum length is not cut."""
        long_name = "N" * MEMBER_NAME_MAX_LENGTH
        self.records.change_member(STUDENT_ID, name=long_name)
        register_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertEqual(self.stored_name(), long_name)

    def test_name_over_length_limit_is_cut(self) -> None:
        """Boundary: one character too many is cut, and registration succeeds."""
        full_length_name = "N" * MEMBER_NAME_MAX_LENGTH
        self.records.change_member(STUDENT_ID, name=full_length_name + "X")
        register_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertEqual(self.stored_name(), full_length_name)


class VerifyOtpTests(RegistrationTestCase):
    """verify_registration_otp: AC 2, 3, 4 and 5."""

    def setUp(self) -> None:
        """Register the student so a valid OTP exists."""
        super().setUp()
        register_user(STUDENT_ID, GOOD_PASSWORD)

    def test_correct_otp_activates_account(self) -> None:
        """AC 2: the correct OTP activates the account and uses the OTP."""
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)
        self.assertTrue(user.is_active)
        self.assertEqual(latest_otp(STUDENT_ID).status, OTP_USED)

    def test_activated_user_can_log_in(self) -> None:
        """AC 2: after activation Django's authentication accepts the user."""
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        user = authenticate(username=STUDENT_ID, password=GOOD_PASSWORD)
        self.assertIsNotNone(user)

    def test_each_role_is_copied_from_records(self) -> None:
        """AC 2: every role in the records is given to the account."""
        for member in TEST_MEMBERS:
            if member.email is None and member.mobile is None:
                continue
            with self.subTest(role=member.role):
                user = self.make_active_user(member.id_number)
                self.assertEqual(user.role, member.role)

    def test_used_otp_cannot_be_used_again(self) -> None:
        """A used OTP no longer works."""
        code = self.sender.last_code
        verify_registration_otp(STUDENT_ID, code)
        with self.assertRaisesMessage(ServiceError, MSG_ALREADY_REGISTERED):
            verify_registration_otp(STUDENT_ID, code)

    def test_wrong_otp_is_rejected_and_user_may_retry(self) -> None:
        """AC 3: a wrong OTP is rejected, then the correct one still works."""
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            verify_registration_otp(STUDENT_ID, self.wrong_code())
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)

    def test_wrong_attempt_is_still_counted_after_error(self) -> None:
        """The wrong attempt is saved even though an error is raised."""
        with self.assertRaises(ServiceError):
            verify_registration_otp(STUDENT_ID, self.wrong_code())
        self.assertEqual(latest_otp(STUDENT_ID).wrong_attempts, 1)

    def test_non_digit_otp_is_rejected_as_incorrect(self) -> None:
        """Invalid input: letters can never match the OTP."""
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            verify_registration_otp(STUDENT_ID, "abcdef")

    def test_second_wrong_otp_keeps_otp_valid(self) -> None:
        """AC 4 boundary: after 2 wrong tries the OTP is still valid."""
        for _ in range(2):
            with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
                verify_registration_otp(STUDENT_ID, self.wrong_code())
        self.assertEqual(latest_otp(STUDENT_ID).status, OTP_VALID)

    def test_third_wrong_otp_invalidates_otp(self) -> None:
        """AC 4: the 3rd wrong try makes the OTP invalid."""
        for _ in range(2):
            with self.assertRaises(ServiceError):
                verify_registration_otp(STUDENT_ID, self.wrong_code())
        with self.assertRaisesMessage(ServiceError, MSG_OTP_NO_LONGER_VALID):
            verify_registration_otp(STUDENT_ID, self.wrong_code())
        otp = latest_otp(STUDENT_ID)
        self.assertEqual(otp.status, OTP_INVALID)
        self.assertEqual(otp.wrong_attempts, 3)

    def test_correct_otp_after_invalidation_is_rejected(self) -> None:
        """AC 4: once invalid, even the correct code needs a new OTP."""
        for _ in range(3):
            with self.assertRaises(ServiceError):
                verify_registration_otp(STUDENT_ID, self.wrong_code())
        with self.assertRaisesMessage(ServiceError, MSG_OTP_NO_LONGER_VALID):
            verify_registration_otp(STUDENT_ID, self.sender.last_code)

    def test_otp_is_accepted_at_four_minutes_fifty_nine(self) -> None:
        """AC 2 boundary: just inside the 5 minutes is accepted."""
        self.move_clock(timedelta(minutes=4, seconds=59))
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        self.assertEqual(latest_otp(STUDENT_ID).status, OTP_USED)

    def test_otp_is_rejected_at_five_minutes_one_second(self) -> None:
        """AC 5 boundary: just after the 5 minutes is expired."""
        self.move_clock(timedelta(minutes=5, seconds=1))
        with self.assertRaisesMessage(ServiceError, MSG_OTP_EXPIRED):
            verify_registration_otp(STUDENT_ID, self.sender.last_code)
        self.assertEqual(latest_otp(STUDENT_ID).status, OTP_EXPIRED)

    def test_second_submit_after_expiry_still_says_expired(self) -> None:
        """AC 5: submitting again after expiry repeats the expired message."""
        self.move_clock(timedelta(minutes=5, seconds=1))
        for _ in range(2):
            with self.assertRaisesMessage(ServiceError, MSG_OTP_EXPIRED):
                verify_registration_otp(STUDENT_ID, self.sender.last_code)

    def test_new_otp_can_be_requested_after_expiry(self) -> None:
        """AC 5: after expiry the user can request and use a new OTP."""
        self.move_clock(timedelta(minutes=6))
        with self.assertRaises(ServiceError):
            verify_registration_otp(STUDENT_ID, self.sender.last_code)
        request_new_registration_otp(STUDENT_ID)
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)

    def test_verify_for_unregistered_id_is_rejected(self) -> None:
        """Exception: there is no account to verify for an unknown ID."""
        with self.assertRaisesMessage(ServiceError, MSG_ID_NOT_FOUND):
            verify_registration_otp(UNKNOWN_ID, self.sender.last_code)


class RequestNewOtpTests(RegistrationTestCase):
    """request_new_registration_otp: AC 6 and 11."""

    def setUp(self) -> None:
        """Register the student; this is the 1st OTP request."""
        super().setUp()
        register_user(STUDENT_ID, GOOD_PASSWORD)

    def test_new_otp_cancels_earlier_otp(self) -> None:
        """AC 6: the earlier OTP is cancelled at once; one OTP stays valid."""
        earlier_otp = latest_otp(STUDENT_ID)
        request_new_registration_otp(STUDENT_ID)
        earlier_otp.refresh_from_db()
        self.assertEqual(earlier_otp.status, OTP_INVALID)
        self.assertEqual(Otp.objects.filter(status=OTP_VALID).count(), 1)

    def test_old_code_is_rejected_after_new_otp(self) -> None:
        """AC 6: the earlier code stops working; the new code works."""
        old_code = self.sender.last_code
        # A fixed new code, so it can never match the old one by chance.
        new_code = self.wrong_code()
        self.start_patch("campus.services._generate_otp_code", new_code)
        request_new_registration_otp(STUDENT_ID)
        with self.assertRaisesMessage(ServiceError, MSG_OTP_INCORRECT):
            verify_registration_otp(STUDENT_ID, old_code)
        verify_registration_otp(STUDENT_ID, new_code)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)

    def test_failed_new_otp_delivery_keeps_previous_otp_valid(self) -> None:
        """Exception: if the new OTP cannot be sent, the earlier one still works."""
        earlier_code = self.sender.last_code
        self.start_patch("campus.services.get_otp_sender", FailingOtpSender())
        with self.assertRaises(ConnectionError):
            request_new_registration_otp(STUDENT_ID)
        self.assertEqual(Otp.objects.count(), 1)
        self.assertEqual(latest_otp(STUDENT_ID).status, OTP_VALID)
        verify_registration_otp(STUDENT_ID, earlier_code)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)

    def test_new_otp_is_sent_and_works(self) -> None:
        """AC 6: the new OTP is sent and activates the account."""
        request_new_registration_otp(STUDENT_ID)
        self.assertEqual(len(self.sender.sent_messages), 2)
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)

    def test_fifth_request_in_window_is_accepted(self) -> None:
        """AC 11 boundary: registration plus 4 new OTPs is 5 requests."""
        for _ in range(4):
            request_new_registration_otp(STUDENT_ID)
        self.assertEqual(len(self.sender.sent_messages), 5)

    def test_sixth_request_in_window_is_rejected(self) -> None:
        """AC 11: the 6th request within 15 minutes is rejected."""
        for _ in range(4):
            request_new_registration_otp(STUDENT_ID)
        with self.assertRaisesMessage(ServiceError, MSG_TOO_MANY_REQUESTS):
            request_new_registration_otp(STUDENT_ID)
        self.assertEqual(len(self.sender.sent_messages), 5)

    def test_rejected_request_keeps_current_otp_valid(self) -> None:
        """AC 11: a rejected request does not cancel the current OTP."""
        for _ in range(4):
            request_new_registration_otp(STUDENT_ID)
        with self.assertRaises(ServiceError):
            request_new_registration_otp(STUDENT_ID)
        verify_registration_otp(STUDENT_ID, self.sender.last_code)

    def test_registering_again_counts_toward_limit(self) -> None:
        """AC 11: registering again is also an OTP request."""
        for _ in range(4):
            register_user(STUDENT_ID, GOOD_PASSWORD)
        with self.assertRaisesMessage(ServiceError, MSG_TOO_MANY_REQUESTS):
            register_user(STUDENT_ID, NEW_PASSWORD)
        user = User.objects.get(username=STUDENT_ID)
        self.assertTrue(user.check_password(GOOD_PASSWORD))

    def test_sixth_request_at_fourteen_fifty_nine_is_rejected(self) -> None:
        """AC 11 boundary: just inside the 15 minutes the limit still applies."""
        for _ in range(4):
            request_new_registration_otp(STUDENT_ID)
        self.move_clock(timedelta(minutes=14, seconds=59))
        with self.assertRaisesMessage(ServiceError, MSG_TOO_MANY_REQUESTS):
            request_new_registration_otp(STUDENT_ID)
        self.assertEqual(len(self.sender.sent_messages), 5)

    def test_sixth_request_at_fifteen_minutes_is_accepted(self) -> None:
        """AC 11 boundary: after 15 minutes the user may request again."""
        for _ in range(4):
            request_new_registration_otp(STUDENT_ID)
        self.move_clock(timedelta(minutes=15))
        request_new_registration_otp(STUDENT_ID)
        self.assertEqual(len(self.sender.sent_messages), 6)

    def test_new_otp_for_unregistered_id_is_rejected(self) -> None:
        """Exception: no pending account exists for an unknown ID."""
        with self.assertRaisesMessage(ServiceError, MSG_ID_NOT_FOUND):
            request_new_registration_otp(UNKNOWN_ID)

    def test_new_otp_for_active_user_is_rejected(self) -> None:
        """An activated account does not need a registration OTP."""
        verify_registration_otp(STUDENT_ID, self.sender.last_code)
        with self.assertRaisesMessage(ServiceError, MSG_ALREADY_REGISTERED):
            request_new_registration_otp(STUDENT_ID)
