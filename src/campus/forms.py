"""Forms that check the SHAPE of user input (Presentation layer).

Forms check only that fields are present and well formed. Business rules,
such as the minimum password length, live in ``services.py``.

The complaint forms check that a photo is really a small JPG or PNG file and
that the chosen location is one of the university's locations, because both
need only the input and the lists in ``constants.py``.
"""

from django import forms
from django.core.files.uploadedfile import UploadedFile

from campus.constants import (
    BROWSABLE_STATUSES,
    BYTES_PER_MEGABYTE,
    CATEGORY_CHOICES,
    COMPLAINT_STATUS_CHOICES,
    DESCRIPTION_MAX_LENGTH,
    ID_NUMBER_MAX_LENGTH,
    LOCATIONS,
    MSG_OTP_FORMAT,
    MSG_PHOTO_INVALID,
    MSG_REASON_REQUIRED,
    MSG_SELECT_CATEGORY,
    MSG_SELECT_LOCATION,
    OTP_PATTERN,
    PHOTO_ALLOWED_EXTENSIONS,
    PHOTO_MAX_MEGABYTES,
    PHOTO_SIGNATURE_BYTES,
    PHOTO_SIGNATURES_HEX,
    REASON_MAX_LENGTH,
)


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


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    """Remove repeated values and empty values, keeping the first order.

    Args:
        values: Values that may repeat, for example every building.

    Returns:
        The distinct non-empty values in their first-seen order.
    """
    return tuple(dict.fromkeys(value for value in values if value))


def _as_choices(values: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Make form choices where the stored value and the label are the same.

    Args:
        values: The values to offer.

    Returns:
        A tuple of (value, label) pairs.
    """
    return tuple((value, value) for value in values)


BUILDING_CHOICES = _as_choices(_unique(tuple(row[0] for row in LOCATIONS)))
FLOOR_CHOICES = _as_choices(_unique(tuple(row[1] for row in LOCATIONS)))
ROOM_CHOICES = _as_choices(_unique(tuple(row[2] for row in LOCATIONS)))
BROWSE_STATUS_CHOICES = tuple(
    choice for choice in COMPLAINT_STATUS_CHOICES if choice[0] in BROWSABLE_STATUSES
)


class CategoryLocationForm(forms.Form):
    """A category and a location, the two things that make a complaint similar.

    Used on its own to look for similar complaints (FR-07) and as the first
    part of the complaint form. A missing part is highlighted with the
    message from the UI design.
    """

    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        error_messages={
            "required": MSG_SELECT_CATEGORY,
            "invalid_choice": MSG_SELECT_CATEGORY,
        },
    )
    building = forms.ChoiceField(
        choices=BUILDING_CHOICES,
        error_messages={
            "required": MSG_SELECT_LOCATION,
            "invalid_choice": MSG_SELECT_LOCATION,
        },
    )
    # A place without a floor (a lift) leaves the floor empty.
    floor = forms.ChoiceField(
        choices=FLOOR_CHOICES,
        required=False,
        error_messages={"invalid_choice": MSG_SELECT_LOCATION},
    )
    room_or_area = forms.ChoiceField(
        choices=ROOM_CHOICES,
        error_messages={
            "required": MSG_SELECT_LOCATION,
            "invalid_choice": MSG_SELECT_LOCATION,
        },
    )

    def clean(self) -> dict[str, object]:
        """Check that the three location parts belong to one real location.

        Returns:
            The cleaned data.
        """
        cleaned_data = super().clean()
        parts = (
            cleaned_data.get("building"),
            cleaned_data.get("floor", ""),
            cleaned_data.get("room_or_area"),
        )
        all_parts_chosen = parts[0] and parts[2]
        if all_parts_chosen and parts not in LOCATIONS:
            self.add_error("room_or_area", MSG_SELECT_LOCATION)
        return cleaned_data

    @property
    def location_errors(self) -> list[str]:
        """Collect the location errors once, so the page shows one message.

        Returns:
            The distinct error messages of the three location fields.
        """
        messages = []
        for name in ("building", "floor", "room_or_area"):
            messages.extend(self.errors.get(name, []))
        return list(dict.fromkeys(messages))


class ComplaintForm(CategoryLocationForm):
    """The complaint form (FR-06, FR-08): details, optional photo, hazard flag."""

    description = forms.CharField(
        required=False, max_length=DESCRIPTION_MAX_LENGTH, widget=forms.Textarea
    )
    photo = forms.FileField(required=False)
    is_safety_hazard = forms.BooleanField(required=False)

    def clean_photo(self) -> UploadedFile | None:
        """Accept only a JPG or PNG file of up to 5 MB (FR-06, NFR-17).

        The file name, the size and the first bytes of the file are checked,
        so a renamed file of another type is rejected too.

        Returns:
            The uploaded file, or None if no photo was attached.

        Raises:
            ValidationError: If the file is not an allowed image.
        """
        photo = self.cleaned_data.get("photo")
        if photo is None:
            return None
        has_allowed_name = photo.name.lower().endswith(PHOTO_ALLOWED_EXTENSIONS)
        if (
            not has_allowed_name
            or photo.size > PHOTO_MAX_MEGABYTES * BYTES_PER_MEGABYTE
        ):
            raise forms.ValidationError(MSG_PHOTO_INVALID)
        header = photo.read(PHOTO_SIGNATURE_BYTES).hex()
        photo.seek(0)
        if not header.startswith(PHOTO_SIGNATURES_HEX):
            raise forms.ValidationError(MSG_PHOTO_INVALID)
        return photo


class ReopenForm(forms.Form):
    """The reopen form: a required short reason (FR-10)."""

    reason = forms.CharField(
        max_length=REASON_MAX_LENGTH,
        widget=forms.Textarea,
        error_messages={"required": MSG_REASON_REQUIRED},
    )


class BrowseFilterForm(forms.Form):
    """The filters of Existing Complaints: building, category, status (FR-21).

    Every field is optional; an empty field means "all".
    """

    building = forms.ChoiceField(choices=BUILDING_CHOICES, required=False)
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, required=False)
    status = forms.ChoiceField(choices=BROWSE_STATUS_CHOICES, required=False)
