"""Shared test support for the staff actions (F5: FR-11 to FR-14, FR-20)."""

from datetime import timedelta

from campus.constants import ROLE_MAINTENANCE_STAFF
from campus.models import Complaint, User
from campus.services import accept_complaint
from campus.tests.base import MOBILE_ONLY_ID
from campus.tests.complaint_base import ComplaintTestCase


class StaffTestCase(ComplaintTestCase):
    """Base class: two maintenance staff members and one supervisor.

    ``self.staff`` and ``self.other_staff`` are maintenance staff,
    ``self.supervisor`` is a supervisor and ``self.student`` a complainant.
    """

    def setUp(self) -> None:
        """Create the staff members on top of the complaint test users."""
        super().setUp()
        self.staff = self.make_active_user(MOBILE_ONLY_ID)
        # The test records hold one staff member; a second one is needed for
        # the "assigned to another staff member" rules.
        User.objects.filter(pk=self.faculty.pk).update(role=ROLE_MAINTENANCE_STAFF)
        self.faculty.refresh_from_db()
        self.other_staff = self.faculty

    def make_in_progress(self, staff: User, **changes: object) -> Complaint:
        """Submit a complaint and let a staff member accept it.

        Args:
            staff: The staff member who accepts it.
            changes: Draft fields to replace.

        Returns:
            The In Progress complaint, reloaded from the database.
        """
        complaint = self.make_complaint(self.student, **changes)
        accept_complaint(staff, complaint.complaint_id)
        complaint.refresh_from_db()
        return complaint

    def clock_at(self, minutes: int) -> None:
        """Set the test clock, so complaints get different times.

        Args:
            minutes: How many minutes after the start time it now is.
        """
        self.move_clock(timedelta(minutes=minutes))
