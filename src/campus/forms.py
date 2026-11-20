"""Forms that check the SHAPE of user input (Presentation layer).

Forms check only that fields are present and well formed. Business rules,
such as the minimum password length, live in ``services.py``.
"""

from django import forms

from campus.constants import ID_NUMBER_MAX_LENGTH, MSG_OTP_FORMAT, OTP_PATTERN


class RegisterForm(forms.Form):
    """The registration form: IUB ID number and a password."""

    id_number = forms.CharField(max_length=ID_NUMBER_MAX_LENGTH)
    # strip=False because spaces are a valid part of a password.
    password = forms.CharField(strip=False, widget=forms.PasswordInput)


class OtpForm(forms.Form):
    """The OTP form: exactly the right number of digits."""

    otp = forms.RegexField(
        regex=OTP_PATTERN, error_messages={"invalid": MSG_OTP_FORMAT}
    )
