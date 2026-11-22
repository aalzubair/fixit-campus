"""Tests for delivery.py: the console sender and the sender factory."""

import io
from contextlib import redirect_stdout

from django.test import SimpleTestCase, override_settings

from campus.delivery import ConsoleOtpSender, get_otp_sender
from campus.tests.base import STUDENT_EMAIL
from campus.tests.fakes import FakeOtpSender

SAMPLE_CODE = "123456"


class ConsoleOtpSenderTests(SimpleTestCase):
    """ConsoleOtpSender prints the OTP for developers."""

    def test_prints_destination_and_code(self) -> None:
        """The printed line shows where the code would go and the code."""
        output = io.StringIO()
        with redirect_stdout(output):
            ConsoleOtpSender().send_otp(STUDENT_EMAIL, SAMPLE_CODE)
        self.assertIn(STUDENT_EMAIL, output.getvalue())
        self.assertIn(SAMPLE_CODE, output.getvalue())


class GetOtpSenderTests(SimpleTestCase):
    """get_otp_sender builds the class named in settings."""

    def test_default_setting_gives_console_sender(self) -> None:
        """Development uses the console sender by default."""
        self.assertIsInstance(get_otp_sender(), ConsoleOtpSender)

    @override_settings(FIXIT_OTP_SENDER="campus.tests.fakes.FakeOtpSender")
    def test_setting_selects_sender_class(self) -> None:
        """Changing the setting swaps the delivery system."""
        self.assertIsInstance(get_otp_sender(), FakeOtpSender)

    @override_settings(FIXIT_OTP_SENDER="campus.delivery.NoSuchSender")
    def test_wrong_setting_raises_import_error(self) -> None:
        """Exception: a setting that names no class fails clearly."""
        with self.assertRaises(ImportError):
            get_otp_sender()
