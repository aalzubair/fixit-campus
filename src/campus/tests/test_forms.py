"""Tests for forms.py: input shape only."""

from django.test import SimpleTestCase

from campus.constants import ID_NUMBER_MAX_LENGTH, MSG_OTP_FORMAT, OTP_LENGTH
from campus.forms import OtpForm, RegisterForm
from campus.tests.base import GOOD_PASSWORD, STUDENT_ID

REQUIRED_MESSAGE = "This field is required."


class RegisterFormTests(SimpleTestCase):
    """RegisterForm needs an ID number and a password."""

    def test_id_and_password_are_valid(self) -> None:
        """Normal input passes."""
        form = RegisterForm({"id_number": STUDENT_ID, "password": GOOD_PASSWORD})
        self.assertTrue(form.is_valid())

    def test_empty_id_is_rejected(self) -> None:
        """Invalid input: the ID number is required."""
        form = RegisterForm({"id_number": "", "password": GOOD_PASSWORD})
        self.assertEqual(form.errors["id_number"], [REQUIRED_MESSAGE])

    def test_empty_password_is_rejected(self) -> None:
        """Invalid input: the password is required."""
        form = RegisterForm({"id_number": STUDENT_ID, "password": ""})
        self.assertEqual(form.errors["password"], [REQUIRED_MESSAGE])

    def test_too_long_id_is_rejected(self) -> None:
        """Boundary: one character over the maximum is rejected."""
        form = RegisterForm(
            {"id_number": "1" * (ID_NUMBER_MAX_LENGTH + 1), "password": GOOD_PASSWORD}
        )
        self.assertIn("id_number", form.errors)

    def test_id_is_stripped_but_password_is_not(self) -> None:
        """Spaces around the ID are removed; spaces in a password are kept."""
        password_with_spaces = f" {GOOD_PASSWORD} "
        form = RegisterForm(
            {"id_number": f" {STUDENT_ID} ", "password": password_with_spaces}
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["id_number"], STUDENT_ID)
        self.assertEqual(form.cleaned_data["password"], password_with_spaces)


class OtpFormTests(SimpleTestCase):
    """OtpForm needs exactly OTP_LENGTH digits."""

    def test_six_digits_are_valid(self) -> None:
        """Normal input passes."""
        self.assertTrue(OtpForm({"otp": "1" * OTP_LENGTH}).is_valid())

    def test_non_digit_otp_is_rejected(self) -> None:
        """Invalid input: letters show the OTP format message."""
        form = OtpForm({"otp": "12ab56"})
        self.assertEqual(form.errors["otp"], [MSG_OTP_FORMAT])

    def test_too_short_and_too_long_otp_are_rejected(self) -> None:
        """Boundary: one digit fewer or one digit more is rejected."""
        for length in (OTP_LENGTH - 1, OTP_LENGTH + 1):
            with self.subTest(length=length):
                form = OtpForm({"otp": "1" * length})
                self.assertEqual(form.errors["otp"], [MSG_OTP_FORMAT])

    def test_empty_otp_is_rejected(self) -> None:
        """Invalid input: the OTP is required."""
        form = OtpForm({"otp": ""})
        self.assertEqual(form.errors["otp"], [REQUIRED_MESSAGE])
