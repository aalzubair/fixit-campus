"""Sending one-time passwords to users by email or SMS.

The real message delivery service is an outside system. The rest of the
code uses only the ``OtpSender`` interface. ``ConsoleOtpSender`` prints the
code and is for development only.
"""

from abc import ABC, abstractmethod

from django.conf import settings
from django.utils.module_loading import import_string

from campus.constants import CONSOLE_OTP_MESSAGE


class OtpSender(ABC):  # pylint: disable=too-few-public-methods
    """Interface for sending an OTP to an email address or mobile number."""

    @abstractmethod
    def send_otp(self, destination: str, code: str) -> None:
        """Send the OTP code to the destination.

        Args:
            destination: An email address or a mobile number.
            code: The plain OTP code.
        """


class ConsoleOtpSender(OtpSender):  # pylint: disable=too-few-public-methods
    """Sender that prints the OTP to the console (development only)."""

    def send_otp(self, destination: str, code: str) -> None:
        """Print the OTP so a developer can copy it.

        Printing a plain OTP is allowed only here, because this sender is
        never used outside development.

        Args:
            destination: An email address or a mobile number.
            code: The plain OTP code.
        """
        print(CONSOLE_OTP_MESSAGE.format(destination=destination, code=code))


def get_otp_sender() -> OtpSender:
    """Create the OTP sender named in ``settings.FIXIT_OTP_SENDER``.

    Returns:
        A new OTP sender.

    Raises:
        ImportError: If the setting does not name an importable class.
    """
    sender_class = import_string(settings.FIXIT_OTP_SENDER)
    return sender_class()
