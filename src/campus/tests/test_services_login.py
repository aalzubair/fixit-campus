"""Tests for the FR-02 login rules in services.py.

Acceptance criteria (AC) numbers refer to SRS FR-02 Confirmation 1 to 8.
"""

from datetime import timedelta

from campus.constants import (
    ACCOUNT_LOCK_MINUTES,
    LOGIN_MAX_FAILED_ATTEMPTS,
    MSG_ACCOUNT_LOCKED,
    MSG_ACCOUNT_NO_LONGER_ACTIVE,
    MSG_INVALID_LOGIN,
    ROLE_FACULTY,
    ROLE_STUDENT,
)
from campus.models import Otp, User
from campus.services import ServiceError, log_in_user, register_user
from campus.tests.base import (
    FACULTY_ID,
    GOOD_PASSWORD,
    NEW_STUDENT_NAME,
    START_TIME,
    STUDENT_ID,
    STUDENT_NAME,
    UNKNOWN_ID,
    WRONG_PASSWORD,
    RegistrationTestCase,
)

LOCK_END = START_TIME + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
ONE_SECOND = timedelta(seconds=1)


def stored_user() -> User:
    """Read the student fresh from the database.

    Returns:
        The stored student user.
    """
    return User.objects.get(username=STUDENT_ID)


class LoginTestCase(RegistrationTestCase):
    """Base class: log_in_user with an active student account."""

    def setUp(self) -> None:
        """Create an active student account."""
        super().setUp()
        self.make_active_user(STUDENT_ID)

    def assert_login_rejected(self, password: str, message: str) -> None:
        """Check that a login is rejected with the given message.

        Args:
            password: The password to try.
            message: The expected user-facing message.
        """
        with self.assertRaisesMessage(ServiceError, message):
            log_in_user(STUDENT_ID, password)


class LoginTests(LoginTestCase):
    """AC 1 and 2: correct and wrong ID or password."""

    def test_correct_password_returns_user(self) -> None:
        """AC 1: the correct ID and password log the user in."""
        user = log_in_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertEqual(user.username, STUDENT_ID)

    def test_wrong_password_is_rejected_with_generic_message(self) -> None:
        """AC 2: a wrong password gives "Invalid ID or password"."""
        self.assert_login_rejected(WRONG_PASSWORD, MSG_INVALID_LOGIN)

    def test_wrong_password_is_counted(self) -> None:
        """Each wrong password adds 1 to the stored count."""
        self.type_wrong_passwords(STUDENT_ID, times=2)
        self.assertEqual(stored_user().failed_login_attempts, 2)

    def test_wrong_three_character_password_counts_as_failed_attempt(self) -> None:
        """No length rule at login: a short wrong password is just wrong."""
        self.assert_login_rejected("abc", MSG_INVALID_LOGIN)
        self.assertEqual(stored_user().failed_login_attempts, 1)

    def test_empty_password_is_rejected(self) -> None:
        """An empty password is a wrong password."""
        self.assert_login_rejected("", MSG_INVALID_LOGIN)

    def test_unknown_id_gets_same_message_and_stores_nothing(self) -> None:
        """An unknown ID gives the same message and adds no rows."""
        users_before = User.objects.count()
        otps_before = Otp.objects.count()
        with self.assertRaisesMessage(ServiceError, MSG_INVALID_LOGIN):
            log_in_user(UNKNOWN_ID, GOOD_PASSWORD)
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(Otp.objects.count(), otps_before)

    def test_empty_id_gets_same_message(self) -> None:
        """An empty ID is treated like an unknown ID."""
        with self.assertRaisesMessage(ServiceError, MSG_INVALID_LOGIN):
            log_in_user("", GOOD_PASSWORD)

    def test_pending_account_gets_same_message(self) -> None:
        """An account that is not activated cannot log in."""
        register_user(FACULTY_ID, GOOD_PASSWORD)
        with self.assertRaisesMessage(ServiceError, MSG_INVALID_LOGIN):
            log_in_user(FACULTY_ID, GOOD_PASSWORD)


class AccountLockTests(LoginTestCase):
    """AC 3, 5 and 6: lock after 5 wrong passwords in a row, for 15 minutes."""

    def test_fourth_wrong_password_does_not_lock(self) -> None:
        """Boundary: 4 wrong passwords leave the account unlocked."""
        self.type_wrong_passwords(STUDENT_ID, times=LOGIN_MAX_FAILED_ATTEMPTS - 1)
        self.assertIsNone(stored_user().locked_until)
        self.assertEqual(log_in_user(STUDENT_ID, GOOD_PASSWORD).username, STUDENT_ID)

    def test_fifth_wrong_password_locks_for_fifteen_minutes(self) -> None:
        """Boundary: the 5th wrong password locks until now + 15 minutes."""
        self.type_wrong_passwords(STUDENT_ID)
        self.assertEqual(stored_user().locked_until, LOCK_END)

    def test_fifth_wrong_password_still_says_invalid(self) -> None:
        """The locking attempt itself does not reveal the lock."""
        self.type_wrong_passwords(STUDENT_ID, times=LOGIN_MAX_FAILED_ATTEMPTS - 1)
        self.assert_login_rejected(WRONG_PASSWORD, MSG_INVALID_LOGIN)

    def test_lock_is_stored_after_the_error_is_raised(self) -> None:
        """The count and the lock are saved, not rolled back with the error."""
        self.type_wrong_passwords(STUDENT_ID, times=LOGIN_MAX_FAILED_ATTEMPTS - 1)
        with self.assertRaises(ServiceError):
            log_in_user(STUDENT_ID, WRONG_PASSWORD)
        user = stored_user()
        self.assertEqual(user.locked_until, LOCK_END)
        self.assertEqual(user.failed_login_attempts, LOGIN_MAX_FAILED_ATTEMPTS)

    def test_try_after_five_wrong_passwords_is_locked(self) -> None:
        """AC 3: after 5 wrong passwords the next try meets the lock."""
        self.type_wrong_passwords(STUDENT_ID)
        self.assert_login_rejected(WRONG_PASSWORD, MSG_ACCOUNT_LOCKED)

    def test_correct_login_resets_count(self) -> None:
        """Wrong passwords must be in a row: a success starts again from 0."""
        self.type_wrong_passwords(STUDENT_ID, times=LOGIN_MAX_FAILED_ATTEMPTS - 1)
        log_in_user(STUDENT_ID, GOOD_PASSWORD)
        self.type_wrong_passwords(STUDENT_ID, times=LOGIN_MAX_FAILED_ATTEMPTS - 1)
        self.assertIsNone(stored_user().locked_until)

    def test_locked_account_rejects_correct_password(self) -> None:
        """AC 5: a locked account rejects even the correct password."""
        self.type_wrong_passwords(STUDENT_ID)
        self.assert_login_rejected(GOOD_PASSWORD, MSG_ACCOUNT_LOCKED)

    def test_wrong_password_while_locked_is_not_counted(self) -> None:
        """Nothing changes while locked: no count, no longer lock."""
        self.type_wrong_passwords(STUDENT_ID)
        self.move_clock(timedelta(minutes=5))
        self.assert_login_rejected(WRONG_PASSWORD, MSG_ACCOUNT_LOCKED)
        user = stored_user()
        self.assertEqual(user.failed_login_attempts, LOGIN_MAX_FAILED_ATTEMPTS)
        self.assertEqual(user.locked_until, LOCK_END)

    def test_lock_still_active_at_fourteen_fifty_nine(self) -> None:
        """Boundary: one second before the lock ends it still holds."""
        self.type_wrong_passwords(STUDENT_ID)
        self.move_clock(timedelta(minutes=ACCOUNT_LOCK_MINUTES) - ONE_SECOND)
        self.assert_login_rejected(GOOD_PASSWORD, MSG_ACCOUNT_LOCKED)

    def test_lock_is_over_at_fifteen_minutes(self) -> None:
        """AC 6, boundary: exactly 15 minutes later the correct password works."""
        self.type_wrong_passwords(STUDENT_ID)
        self.move_clock(timedelta(minutes=ACCOUNT_LOCK_MINUTES))
        log_in_user(STUDENT_ID, GOOD_PASSWORD)
        user = stored_user()
        self.assertEqual(user.failed_login_attempts, 0)
        self.assertIsNone(user.locked_until)

    def test_count_restarts_from_zero_after_lock_expired(self) -> None:
        """After the lock, one wrong password counts as the first, not the 6th."""
        self.type_wrong_passwords(STUDENT_ID)
        self.move_clock(timedelta(minutes=ACCOUNT_LOCK_MINUTES))
        self.assert_login_rejected(WRONG_PASSWORD, MSG_INVALID_LOGIN)
        user = stored_user()
        self.assertEqual(user.failed_login_attempts, 1)
        self.assertIsNone(user.locked_until)

    def test_account_locks_again_after_five_more_wrong_passwords(self) -> None:
        """A new lock needs 5 new wrong passwords after the old lock ended."""
        self.type_wrong_passwords(STUDENT_ID)
        self.move_clock(timedelta(minutes=ACCOUNT_LOCK_MINUTES))
        self.type_wrong_passwords(STUDENT_ID)
        second_lock_end = LOCK_END + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
        self.assertEqual(stored_user().locked_until, second_lock_end)


class RecordsCheckAtLoginTests(LoginTestCase):
    """AC 7 and 8: the IUB records are checked at every login."""

    def test_member_no_longer_in_records_is_rejected(self) -> None:
        """AC 7: a member who left the university cannot log in."""
        self.records.remove_member(STUDENT_ID)
        self.assert_login_rejected(GOOD_PASSWORD, MSG_ACCOUNT_NO_LONGER_ACTIVE)

    def test_records_are_checked_only_after_correct_password(self) -> None:
        """A wrong password never reveals that a member has left."""
        self.records.remove_member(STUDENT_ID)
        self.assert_login_rejected(WRONG_PASSWORD, MSG_INVALID_LOGIN)

    def test_changed_role_in_records_is_stored_at_login(self) -> None:
        """AC 8: the role from the records replaces the stored role."""
        self.records.change_member(STUDENT_ID, role=ROLE_FACULTY)
        user = log_in_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertEqual(user.role, ROLE_FACULTY)
        self.assertEqual(stored_user().role, ROLE_FACULTY)

    def test_role_is_not_changed_by_wrong_password(self) -> None:
        """The stored role changes only on a successful login."""
        self.records.change_member(STUDENT_ID, role=ROLE_FACULTY)
        self.assert_login_rejected(WRONG_PASSWORD, MSG_INVALID_LOGIN)
        self.assertEqual(stored_user().role, ROLE_STUDENT)

    def test_changed_name_in_records_is_stored_at_login(self) -> None:
        """The name from the records replaces the stored name, like the role."""
        self.records.change_member(STUDENT_ID, name=NEW_STUDENT_NAME)
        user = log_in_user(STUDENT_ID, GOOD_PASSWORD)
        self.assertEqual(user.get_full_name(), NEW_STUDENT_NAME)
        self.assertEqual(stored_user().get_full_name(), NEW_STUDENT_NAME)

    def test_name_is_not_changed_by_wrong_password(self) -> None:
        """The stored name changes only on a successful login."""
        self.records.change_member(STUDENT_ID, name=NEW_STUDENT_NAME)
        self.assert_login_rejected(WRONG_PASSWORD, MSG_INVALID_LOGIN)
        self.assertEqual(stored_user().get_full_name(), STUDENT_NAME)
