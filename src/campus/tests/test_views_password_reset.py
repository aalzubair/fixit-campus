"""Tests for the FR-04 password-reset pages (views, urls and templates).

Acceptance criteria (AC) numbers refer to SRS FR-04 Confirmation 1 to 11.
"""

from http import HTTPStatus

from django.http import HttpResponse
from django.urls import reverse

from campus.constants import (
    MSG_ACCOUNT_LOCKED,
    MSG_NEW_OTP_SENT,
    MSG_OTP_FORMAT,
    MSG_OTP_INCORRECT,
    MSG_PASSWORD_CHANGED,
    MSG_PASSWORD_TOO_SHORT,
    MSG_RESET_OTP_SENT,
    MSG_TOO_MANY_REQUESTS,
    OTP_REQUEST_LIMIT,
    PASSWORD_MIN_LENGTH,
    SESSION_RESET_ID_NUMBER,
    TEMPLATE_PASSWORD_RESET,
    TEMPLATE_PASSWORD_RESET_VERIFY,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_PASSWORD_RESET,
    URL_NAME_PASSWORD_RESET_NEW_OTP,
    URL_NAME_PASSWORD_RESET_VERIFY,
)
from campus.tests.base import (
    NEW_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_ID,
    UNKNOWN_ID,
    RegistrationTestCase,
)

RESET_URL = reverse(URL_NAME_PASSWORD_RESET)
VERIFY_URL = reverse(URL_NAME_PASSWORD_RESET_VERIFY)
NEW_OTP_URL = reverse(URL_NAME_PASSWORD_RESET_NEW_OTP)
LOGIN_URL = reverse(URL_NAME_LOGIN)


class ResetPageTestCase(RegistrationTestCase):
    """Base class: an active student and form helpers."""

    def setUp(self) -> None:
        """Create an active student and remember how many OTPs were sent."""
        super().setUp()
        self.make_active_user(STUDENT_ID)
        self.sent_before = len(self.sender.sent_messages)

    def post_reset(self, id_number: str) -> HttpResponse:
        """Submit the first reset form and follow the redirect.

        Args:
            id_number: The IUB ID number to submit.

        Returns:
            The final test client response.
        """
        return self.client.post(RESET_URL, {"id_number": id_number}, follow=True)

    def post_verify(self, otp: str, new_password: str = NEW_PASSWORD) -> HttpResponse:
        """Submit the OTP and the new password.

        Args:
            otp: The OTP to submit.
            new_password: The new password to submit.

        Returns:
            The test client response.
        """
        return self.client.post(VERIFY_URL, {"otp": otp, "new_password": new_password})


class ResetRequestPageTests(ResetPageTestCase):
    """The /password-reset/ page."""

    def test_page_shows_form(self) -> None:
        """The page shows the ID form."""
        self.assertTemplateUsed(self.client.get(RESET_URL), TEMPLATE_PASSWORD_RESET)

    def test_login_page_links_here(self) -> None:
        """The "Forgot password?" link on the login page opens this page."""
        self.assertContains(self.client.get(LOGIN_URL), f'href="{RESET_URL}"')

    def test_registered_id_sends_otp_and_shows_verify_page(self) -> None:
        """AC 1: an OTP is sent and the OTP page shows the message."""
        response = self.post_reset(STUDENT_ID)
        self.assertRedirects(response, VERIFY_URL)
        self.assertContains(response, MSG_RESET_OTP_SENT)
        self.assertEqual(self.sender.last_destination, STUDENT_EMAIL)
        self.assertEqual(self.client.session[SESSION_RESET_ID_NUMBER], STUDENT_ID)

    def test_unknown_id_shows_same_message_and_sends_nothing(self) -> None:
        """AC 8: an unknown ID looks exactly like a registered one."""
        response = self.post_reset(UNKNOWN_ID)
        self.assertRedirects(response, VERIFY_URL)
        self.assertContains(response, MSG_RESET_OTP_SENT)
        self.assertEqual(len(self.sender.sent_messages), self.sent_before)

    def test_member_no_longer_in_records_shows_same_message(self) -> None:
        """AC 8: a member who left the university gets the same message."""
        self.records.remove_member(STUDENT_ID)
        response = self.post_reset(STUDENT_ID)
        self.assertContains(response, MSG_RESET_OTP_SENT)
        self.assertEqual(len(self.sender.sent_messages), self.sent_before)

    def test_locked_account_shows_locked_message(self) -> None:
        """AC 11: a locked account stays on the page with the message."""
        self.type_wrong_passwords(STUDENT_ID)
        response = self.post_reset(STUDENT_ID)
        self.assertTemplateUsed(response, TEMPLATE_PASSWORD_RESET)
        self.assertContains(response, MSG_ACCOUNT_LOCKED)

    def test_too_many_requests_shows_message(self) -> None:
        """AC 10: the 6th request in 15 minutes is refused."""
        for _ in range(OTP_REQUEST_LIMIT):
            self.post_reset(STUDENT_ID)
        self.assertContains(self.post_reset(STUDENT_ID), MSG_TOO_MANY_REQUESTS)

    def test_empty_id_shows_required_error(self) -> None:
        """An empty ID is stopped by the form."""
        response = self.client.post(RESET_URL, {"id_number": ""})
        self.assertEqual(response.context["form"].errors.keys(), {"id_number"})


class ResetVerifyPageTests(ResetPageTestCase):
    """The /password-reset/verify/ page and its new-OTP button."""

    def setUp(self) -> None:
        """Ask for a reset through the page, so the ID is in the session."""
        super().setUp()
        self.post_reset(STUDENT_ID)

    def test_page_shows_form(self) -> None:
        """The page shows the OTP and new-password form."""
        response = self.client.get(VERIFY_URL)
        self.assertTemplateUsed(response, TEMPLATE_PASSWORD_RESET_VERIFY)
        self.assertContains(response, "Request a new OTP")

    def test_without_session_redirects_to_reset_page(self) -> None:
        """The OTP page needs a reset started in this session."""
        self.client.logout()
        self.assertRedirects(self.client.get(VERIFY_URL), RESET_URL)

    def test_correct_otp_changes_password_and_shows_login(self) -> None:
        """AC 2: the password changes and the user can log in with it."""
        response = self.client.post(
            VERIFY_URL,
            {"otp": self.sender.last_code, "new_password": NEW_PASSWORD},
            follow=True,
        )
        self.assertRedirects(response, LOGIN_URL)
        self.assertContains(response, MSG_PASSWORD_CHANGED)
        self.assertNotIn(SESSION_RESET_ID_NUMBER, self.client.session)
        response = self.client.post(
            LOGIN_URL, {"id_number": STUDENT_ID, "password": NEW_PASSWORD}
        )
        self.assertRedirects(response, reverse(URL_NAME_HOME))

    def test_wrong_otp_shows_message(self) -> None:
        """AC 3: a wrong OTP shows the message and the form again."""
        response = self.post_verify(self.wrong_code())
        self.assertContains(response, MSG_OTP_INCORRECT)
        self.assertTemplateUsed(response, TEMPLATE_PASSWORD_RESET_VERIFY)

    def test_short_password_shows_message(self) -> None:
        """AC 9: a 7-character password shows the SRS message."""
        short_password = "x" * (PASSWORD_MIN_LENGTH - 1)
        response = self.post_verify(self.sender.last_code, short_password)
        self.assertContains(response, MSG_PASSWORD_TOO_SHORT)

    def test_non_digit_otp_shows_format_message(self) -> None:
        """A badly shaped OTP is stopped by the form."""
        self.assertContains(self.post_verify("12ab56"), MSG_OTP_FORMAT)

    def test_empty_new_password_shows_required_error(self) -> None:
        """An empty new password is stopped by the form."""
        response = self.post_verify(self.sender.last_code, "")
        self.assertEqual(response.context["form"].errors.keys(), {"new_password"})

    def test_new_otp_button_sends_otp_and_shows_message(self) -> None:
        """AC 6: the button sends a new OTP and says the old one is cancelled."""
        sent_before_button = len(self.sender.sent_messages)
        response = self.client.post(NEW_OTP_URL, follow=True)
        self.assertRedirects(response, VERIFY_URL)
        self.assertContains(response, MSG_NEW_OTP_SENT)
        self.assertEqual(len(self.sender.sent_messages), sent_before_button + 1)

    def test_new_otp_button_too_many_requests_shows_message(self) -> None:
        """AC 10 through the button: 1 request in setUp plus 4, then refused."""
        for _ in range(OTP_REQUEST_LIMIT - 1):
            self.client.post(NEW_OTP_URL)
        response = self.client.post(NEW_OTP_URL, follow=True)
        self.assertContains(response, MSG_TOO_MANY_REQUESTS)

    def test_new_otp_with_get_is_not_allowed(self) -> None:
        """The new-OTP button is POST only."""
        response = self.client.get(NEW_OTP_URL)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_new_otp_without_session_redirects_to_reset_page(self) -> None:
        """The button needs a reset started in this session."""
        self.client.logout()
        self.assertRedirects(self.client.post(NEW_OTP_URL), RESET_URL)
