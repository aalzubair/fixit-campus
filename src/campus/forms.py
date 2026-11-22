"""Forms that check the SHAPE of user input (Presentation layer).

Forms check only that fields are present and well formed. Business rules,
such as the minimum password length, live in ``services.py``.
"""

from django import forms

from campus.constants import ID_NUMBER_MAX_LENGTH, MSG_OTP_FORMAT, OTP_PATTERN


def _password_field() -> forms.CharField:
    """Make a required password field that keeps spaces.

    Returns:
        A new password field. ``strip=False`` because spaces are a valid
        part of a password.
    """
    return forms.CharField(strip=False, widget=forms.PasswordInput)


class IdNumberForm(forms.Form):
    """A form with only the IUB ID number."""

    id_number = forms.CharField(max_length=ID_NUMBER_MAX_LENGTH)


class RegisterForm(IdNumberForm):
    """The registration form: IUB ID number and a password."""

    password = _password_field()


class LoginForm(RegisterForm):
    """The login form: the same two fields as the registration form."""


class PasswordResetRequestForm(IdNumberForm):
    """The first password-reset form: only the IUB ID number."""


class OtpForm(forms.Form):
    """The OTP form: exactly the right number of digits."""

    otp = forms.RegexField(
        regex=OTP_PATTERN, error_messages={"invalid": MSG_OTP_FORMAT}
    )


class PasswordResetVerifyForm(OtpForm):
    """The second password-reset form: the OTP and a new password."""

    new_password = _password_field()
