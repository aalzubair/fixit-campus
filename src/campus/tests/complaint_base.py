"""Shared test support for the complaint features (F3 and F4)."""

import shutil
import tempfile
from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from campus.constants import COMPLAINT_RESOLVED, LOCATIONS
from campus.models import Complaint, User
from campus.services import ComplaintDraft, submit_complaint
from campus.tests.base import (
    ADMINISTRATOR_ID,
    FACULTY_ID,
    STUDENT_ID,
    SUPERVISOR_ID,
    RegistrationTestCase,
)

JPEG_START = b"\xff\xd8\xff\xe0"
PNG_START = b"\x89PNG\r\n\x1a\n"
FIVE_MEGABYTES = 5 * 1024 * 1024
SECRET_TEXT = "SECRET-DESCRIPTION-TEXT"
# One real location of the approved list, and a different one.
BUILDING, FLOOR, ROOM = LOCATIONS[2]
OTHER_BUILDING, OTHER_FLOOR, OTHER_ROOM = LOCATIONS[3]
# The same two places as ready-made form and draft fields.
PLACE = {"building": BUILDING, "floor": FLOOR, "room_or_area": ROOM}
OTHER_PLACE = {
    "building": OTHER_BUILDING,
    "floor": OTHER_FLOOR,
    "room_or_area": OTHER_ROOM,
}


def make_image(name: str = "photo.jpg", size: int = 1000) -> SimpleUploadedFile:
    """Build an uploaded image whose first bytes match its file type.

    Args:
        name: The file name; ``.png`` gets PNG bytes, anything else JPG bytes.
        size: The total size in bytes.

    Returns:
        An uploaded file of exactly ``size`` bytes.
    """
    start = PNG_START if name.lower().endswith(".png") else JPEG_START
    return SimpleUploadedFile(name, start + b"0" * (size - len(start)))


class ComplaintTestCase(RegistrationTestCase):
    """Base class: four active users and a temporary folder for photos.

    ``self.student`` and ``self.faculty`` may submit complaints,
    ``self.administrator`` too; ``self.supervisor`` may not (FR-06).
    """

    def setUp(self) -> None:
        """Create the users and point photo storage to a temporary folder."""
        super().setUp()
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        self.enterContext(self.settings(MEDIA_ROOT=folder))
        self.student = self.make_active_user(STUDENT_ID)
        self.faculty = self.make_active_user(FACULTY_ID)
        self.administrator = self.make_active_user(ADMINISTRATOR_ID)
        self.supervisor = self.make_active_user(SUPERVISOR_ID)

    def make_draft(self, **changes: object) -> ComplaintDraft:
        """Build a valid complaint draft, with optional changes.

        Args:
            changes: Draft fields to replace.

        Returns:
            A draft for an Electrical complaint at the first test location.
        """
        values = {
            "category": "electrical",
            **PLACE,
            "description": "The light flickers.",
            "photo": None,
            "is_safety_hazard": False,
        }
        values.update(changes)
        return ComplaintDraft(**values)

    def make_complaint(self, user: User, **changes: object) -> Complaint:
        """Submit a complaint through the real service.

        Args:
            user: The complainant.
            changes: Draft fields to replace.

        Returns:
            The saved complaint.
        """
        return submit_complaint(user, self.make_draft(**changes))

    def make_resolved(self, user: User, resolved_at: datetime) -> Complaint:
        """Submit a complaint and mark it Resolved at a given time.

        Args:
            user: The complainant.
            resolved_at: When it was resolved.

        Returns:
            The complaint, reloaded from the database.
        """
        complaint = self.make_complaint(user)
        Complaint.objects.filter(pk=complaint.pk).update(
            status=COMPLAINT_RESOLVED, resolved_at=resolved_at
        )
        complaint.refresh_from_db()
        return complaint

    def client_for(self, user: User) -> Client:
        """Make a test browser that is logged in as the user.

        Args:
            user: The user to log in.

        Returns:
            A logged-in test client.
        """
        client = Client()
        client.force_login(user)
        return client

    def form_data(self, **changes: object) -> dict[str, object]:
        """Build the posted data of a valid complaint form.

        Args:
            changes: Fields to replace; use ``None`` to leave a field out.

        Returns:
            The form data for the test client.
        """
        data = {
            "category": "electrical",
            **PLACE,
            "description": "The light flickers.",
        }
        data.update(changes)
        return {key: value for key, value in data.items() if value is not None}
