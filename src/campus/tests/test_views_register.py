"""Tests for the FR-01 registration pages (views, urls and templates)."""

from django.http import HttpResponse
from django.urls import reverse

from campus.constants import (
    ACCOUNT_ACTIVE,
    MSG_ALREADY_REGISTERED,
    MSG_ID_NOT_FOUND,
    MSG_NEW_OTP_SENT,
    MSG_NO_CONTACT_DETAILS,
    MSG_OTP_FORMAT,
    MSG_OTP_INCORRECT,
    MSG_PASSWORD_TOO_SHORT,
    MSG_TOO_MANY_REQUESTS,
    PASSWORD_MIN_LENGTH,
    SESSION_REGISTER_ID_NUMBER,
    TEMPLATE_REGISTER,
    TEMPLATE_REGISTER_DONE,
    TEMPLATE_REGISTER_VERIFY,
    URL_NAME_REGISTER,
    URL_NAME_REGISTER_DONE,
    URL_NAME_REGISTER_NEW_OTP,
    URL_NAME_REGISTER_VERIFY,
)
from campus.models import User
from campus.tests.base import (
    GOOD_PASSWORD,
    NO_CONTACT_ID,
    STUDENT_ID,
    UNKNOWN_ID,
    RegistrationTestCase,
)

REGISTER_URL = reverse(URL_NAME_REGISTER)
VERIFY_URL = reverse(URL_NAME_REGISTER_VERIFY)
NEW_OTP_URL = reverse(URL_NAME_REGISTER_NEW_OTP)
DONE_URL = reverse(URL_NAME_REGISTER_DONE)
METHOD_NOT_ALLOWED = 405


class RegisterPageTests(RegistrationTestCase):
    """The /register/ page."""

    def post_register(
        self, id_number: str, password: str = GOOD_PASSWORD
    ) -> HttpResponse:
        """Submit the registration form.

        Args:
            id_number: The IUB ID number to submit.
            password: The password to submit.

        Returns:
            The test client response.
        """
        return self.client.post(
            REGISTER_URL, {"id_number": id_number, "password": password}
        )

    def test_page_shows_form(self) -> None:
        """GET shows the registration template."""
        response = self.client.get(REGISTER_URL)
        self.assertTemplateUsed(response, TEMPLATE_REGISTER)

    def test_success_redirects_to_verify_and_keeps_id_in_session(self) -> None:
        """AC 1: a valid registration goes to the OTP page."""
        response = self.post_register(STUDENT_ID)
        self.assertRedirects(response, VERIFY_URL)
        self.assertEqual(self.client.session[SESSION_REGISTER_ID_NUMBER], STUDENT_ID)

    def test_unknown_id_shows_message(self) -> None:
        """AC 7: the exact message is shown."""
        self.assertContains(self.post_register(UNKNOWN_ID), MSG_ID_NOT_FOUND)

    def test_already_registered_id_shows_message(self) -> None:
        """AC 8: the exact message is shown."""
        self.make_active_user(STUDENT_ID)
        self.assertContains(self.post_register(STUDENT_ID), MSG_ALREADY_REGISTERED)

    def test_short_password_shows_message(self) -> None:
        """AC 9: the exact message is shown."""
        response = self.post_register(STUDENT_ID, "a" * (PASSWORD_MIN_LENGTH - 1))
        self.assertContains(response, MSG_PASSWORD_TOO_SHORT)

    def test_no_contact_details_shows_message(self) -> None:
        """AC 10: the exact message is shown."""
        response = self.post_register(NO_CONTACT_ID)
        self.assertContains(response, MSG_NO_CONTACT_DETAILS)

    def test_empty_fields_show_required_errors(self) -> None:
        """Invalid input: empty fields are rejected before any service call."""
        response = self.post_register("", "")
        self.assertContains(response, "This field is required.", count=2)
        self.assertEqual(self.sender.sent_messages, [])


class VerifyPageTests(RegistrationTestCase):
    """The /register/verify/ page and the new-OTP button."""

    def setUp(self) -> None:
        """Register through the page so the session holds the ID."""
        super().setUp()
        self.client.post(
            REGISTER_URL, {"id_number": STUDENT_ID, "password": GOOD_PASSWORD}
        )

    def test_page_shows_form(self) -> None:
        """GET shows the OTP template."""
        response = self.client.get(VERIFY_URL)
        self.assertTemplateUsed(response, TEMPLATE_REGISTER_VERIFY)

    def test_without_session_redirects_to_register(self) -> None:
        """A visitor who has not registered is sent to /register/."""
        self.client.cookies.clear()
        self.assertRedirects(self.client.get(VERIFY_URL), REGISTER_URL)

    def test_correct_otp_activates_and_redirects_to_done(self) -> None:
        """AC 2: success activates the account and clears the session."""
        response = self.client.post(VERIFY_URL, {"otp": self.sender.last_code})
        self.assertRedirects(response, DONE_URL)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.account_status, ACCOUNT_ACTIVE)
        self.assertNotIn(SESSION_REGISTER_ID_NUMBER, self.client.session)

    def test_wrong_otp_shows_message(self) -> None:
        """AC 3: the wrong-OTP message is shown on the same page."""
        response = self.client.post(VERIFY_URL, {"otp": self.wrong_code()})
        self.assertContains(response, MSG_OTP_INCORRECT)

    def test_non_digit_otp_shows_format_message(self) -> None:
        """Invalid input: letters are rejected by the form."""
        response = self.client.post(VERIFY_URL, {"otp": "12ab56"})
        self.assertContains(response, MSG_OTP_FORMAT)

    def test_new_otp_button_sends_otp_and_shows_message(self) -> None:
        """AC 6: a new OTP is sent and the page confirms it."""
        response = self.client.post(NEW_OTP_URL, follow=True)
        self.assertRedirects(response, VERIFY_URL)
        self.assertContains(response, MSG_NEW_OTP_SENT)
        self.assertEqual(len(self.sender.sent_messages), 2)

    def test_too_many_requests_shows_message(self) -> None:
        """AC 11: the 6th request shows the exact message."""
        for _ in range(4):
            self.client.post(NEW_OTP_URL)
        response = self.client.post(NEW_OTP_URL, follow=True)
        self.assertContains(response, MSG_TOO_MANY_REQUESTS)

    def test_new_otp_with_get_is_not_allowed(self) -> None:
        """Requesting a new OTP changes data, so it must be a POST."""
        response = self.client.get(NEW_OTP_URL)
        self.assertEqual(response.status_code, METHOD_NOT_ALLOWED)

    def test_new_otp_without_session_redirects_to_register(self) -> None:
        """A visitor who has not registered is sent to /register/."""
        self.client.cookies.clear()
        self.assertRedirects(self.client.post(NEW_OTP_URL), REGISTER_URL)


class DonePageTests(RegistrationTestCase):
    """The /register/done/ page."""

    def test_page_shows_confirmation(self) -> None:
        """The success page uses its template."""
        response = self.client.get(DONE_URL)
        self.assertTemplateUsed(response, TEMPLATE_REGISTER_DONE)
