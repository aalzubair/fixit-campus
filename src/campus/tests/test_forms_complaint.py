"""Tests for the complaint, reopen and browse-filter forms."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from campus.constants import (
    MSG_PHOTO_INVALID,
    MSG_REASON_REQUIRED,
    MSG_SELECT_CATEGORY,
    MSG_SELECT_LOCATION,
)
from campus.forms import BrowseFilterForm, ComplaintForm, ReopenForm
from campus.tests.complaint_base import (
    FIVE_MEGABYTES,
    OTHER_BUILDING,
    PLACE,
    make_image,
)


def valid_data(**changes: object) -> dict[str, object]:
    """Build valid complaint form data.

    Args:
        changes: Fields to replace.

    Returns:
        The posted data.
    """
    data = {"category": "electrical", **PLACE}
    data.update(changes)
    return data


class ComplaintFormTests(SimpleTestCase):
    """The complaint form (FR-06, FR-08)."""

    def test_valid_data_without_photo_or_description(self) -> None:
        """Only category and location are required."""
        form = ComplaintForm(valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["is_safety_hazard"])
        self.assertIsNone(form.cleaned_data["photo"])

    def test_missing_category_message(self) -> None:
        """No category gives the message of the UI design."""
        form = ComplaintForm(valid_data(category=""))
        self.assertEqual(form.errors["category"], [MSG_SELECT_CATEGORY])

    def test_missing_location_gives_one_message(self) -> None:
        """No building, floor or room gives the location message once."""
        form = ComplaintForm(valid_data(building="", floor="", room_or_area=""))
        self.assertEqual(form.location_errors, [MSG_SELECT_LOCATION])

    def test_location_that_does_not_exist_is_rejected(self) -> None:
        """A building, floor and room that do not belong together are rejected."""
        form = ComplaintForm(valid_data(building=OTHER_BUILDING))
        self.assertEqual(form.location_errors, [MSG_SELECT_LOCATION])

    def test_place_without_floor_is_valid(self) -> None:
        """A lift has no floor, so an empty floor is accepted for it."""
        data = valid_data(building="Block C", floor="", room_or_area="Lift 2")
        self.assertTrue(ComplaintForm(data).is_valid())

    def test_unknown_category_is_rejected(self) -> None:
        """A category outside the list is rejected."""
        form = ComplaintForm(valid_data(category="made-up"))
        self.assertEqual(form.errors["category"], [MSG_SELECT_CATEGORY])

    def test_safety_hazard_flag_is_read(self) -> None:
        """A ticked checkbox gives True (FR-08)."""
        form = ComplaintForm(valid_data(is_safety_hazard="on"))
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["is_safety_hazard"])

    def test_jpg_and_png_are_accepted(self) -> None:
        """Both allowed image types pass."""
        for name in ("a.jpg", "b.JPEG", "c.png"):
            with self.subTest(name=name):
                form = ComplaintForm(valid_data(), {"photo": make_image(name)})
                self.assertTrue(form.is_valid(), form.errors)

    def test_other_file_types_are_rejected(self) -> None:
        """A GIF or a PDF is not accepted."""
        for name in ("a.gif", "b.pdf", "c.txt"):
            with self.subTest(name=name):
                photo = SimpleUploadedFile(name, b"\xff\xd8\xff" + b"0" * 50)
                form = ComplaintForm(valid_data(), {"photo": photo})
                self.assertEqual(form.errors["photo"], [MSG_PHOTO_INVALID])

    def test_renamed_file_is_rejected(self) -> None:
        """A text file renamed to .jpg fails the file-signature check."""
        photo = SimpleUploadedFile("fake.jpg", b"this is not an image")
        form = ComplaintForm(valid_data(), {"photo": photo})
        self.assertEqual(form.errors["photo"], [MSG_PHOTO_INVALID])

    def test_file_of_exactly_five_megabytes_is_accepted(self) -> None:
        """The limit is "up to 5 MB", so exactly 5 MB passes."""
        photo = make_image("big.jpg", FIVE_MEGABYTES)
        self.assertTrue(ComplaintForm(valid_data(), {"photo": photo}).is_valid())

    def test_file_over_five_megabytes_is_rejected(self) -> None:
        """One byte over 5 MB is rejected."""
        photo = make_image("big.jpg", FIVE_MEGABYTES + 1)
        form = ComplaintForm(valid_data(), {"photo": photo})
        self.assertEqual(form.errors["photo"], [MSG_PHOTO_INVALID])


class ReopenFormTests(SimpleTestCase):
    """The reopen form (FR-10)."""

    def test_reason_is_required(self) -> None:
        """No reason gives "Please enter a reason."."""
        form = ReopenForm({"reason": ""})
        self.assertEqual(form.errors["reason"], [MSG_REASON_REQUIRED])

    def test_spaces_only_count_as_no_reason(self) -> None:
        """A reason made of spaces is the same as no reason."""
        form = ReopenForm({"reason": "    "})
        self.assertEqual(form.errors["reason"], [MSG_REASON_REQUIRED])

    def test_reason_is_accepted(self) -> None:
        """A short reason passes."""
        self.assertTrue(ReopenForm({"reason": "Still broken."}).is_valid())


class BrowseFilterFormTests(SimpleTestCase):
    """The filters of Existing Complaints (FR-21)."""

    def test_no_filters_is_valid(self) -> None:
        """Every filter is optional."""
        self.assertTrue(BrowseFilterForm({}).is_valid())

    def test_resolved_is_not_a_browse_status(self) -> None:
        """Only Open and In Progress can be chosen as a status filter."""
        self.assertFalse(BrowseFilterForm({"status": "resolved"}).is_valid())
        self.assertTrue(BrowseFilterForm({"status": "in_progress"}).is_valid())
