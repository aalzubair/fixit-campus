"""Tests for the staff action services (F5: FR-11 to FR-14, FR-20)."""

from campus.constants import (
    COMPLAINT_IN_PROGRESS,
    COMPLAINT_OPEN,
    COMPLAINT_REJECTED,
    COMPLAINT_RESOLVED,
    MSG_ACCEPT_FIRST,
    MSG_COMPLAINT_ALREADY_ASSIGNED,
    MSG_COMPLAINT_NOT_FOUND,
    MSG_NOT_AUTHORIZED,
    MSG_ONLY_ACTIVE_CAN_REJECT,
    MSG_ONLY_ASSIGNED_CAN_REJECT,
    MSG_ONLY_ASSIGNED_CAN_RESOLVE,
    MSG_ONLY_IN_PROGRESS_CAN_RESOLVE,
    MSG_ONLY_OPEN_CAN_ACCEPT,
    MSG_ONLY_STAFF_CAN_REJECT,
)
from campus.models import Complaint
from campus.services import (
    ServiceError,
    StaffFilters,
    accept_complaint,
    get_staff_complaint_detail,
    list_staff_complaints,
    reject_complaint,
    resolve_complaint,
)
from campus.tests.base import START_TIME
from campus.tests.complaint_base import OTHER_PLACE
from campus.tests.staff_base import StaffTestCase

REASON = "Not a maintenance issue."
UNKNOWN_COMPLAINT_ID = "CMP-2026-99999"


class ListStaffComplaintsTests(StaffTestCase):
    """FR-11: the staff list, its filters and its order."""

    def test_list_shows_every_status_with_safety_hazard_first(self) -> None:
        """Safety Hazard complaints come first, then the newest (Confirmation 1)."""
        older_hazard = self.make_complaint(self.student, is_safety_hazard=True)
        self.clock_at(5)
        newer = self.make_complaint(self.student)
        self.clock_at(10)
        rejected = self.make_complaint(self.student)
        reject_complaint(self.staff, rejected.complaint_id, REASON)
        listed = list_staff_complaints(StaffFilters())
        self.assertEqual(listed, [older_hazard, rejected, newer])

    def test_filters_must_all_match(self) -> None:
        """Only complaints matching every chosen filter are shown (Confirmation 2)."""
        match = self.make_complaint(self.student, category="plumbing")
        self.make_complaint(self.student, category="electrical")
        self.make_complaint(self.student, category="plumbing", **OTHER_PLACE)
        filters = StaffFilters(
            building=match.building, category="plumbing", status=COMPLAINT_OPEN
        )
        self.assertEqual(list_staff_complaints(filters), [match])

    def test_status_filter_can_show_rejected_complaints(self) -> None:
        """Staff can filter by every status, also Rejected."""
        rejected = self.make_complaint(self.student)
        reject_complaint(self.staff, rejected.complaint_id, REASON)
        self.make_complaint(self.student)
        filters = StaffFilters(status=COMPLAINT_REJECTED)
        self.assertEqual(list_staff_complaints(filters), [rejected])

    def test_safety_hazard_filter_shows_only_flagged(self) -> None:
        """The Safety Hazard filter shows only flagged complaints (Confirmation 3)."""
        hazard = self.make_complaint(self.student, is_safety_hazard=True)
        self.make_complaint(self.student)
        filters = StaffFilters(safety_hazard_only=True)
        self.assertEqual(list_staff_complaints(filters), [hazard])

    def test_filters_with_no_match_give_an_empty_list(self) -> None:
        """No match gives an empty list; the page shows the message (Confirmation 4)."""
        self.make_complaint(self.student)
        filters = StaffFilters(status=COMPLAINT_RESOLVED)
        self.assertEqual(list_staff_complaints(filters), [])


class AcceptComplaintTests(StaffTestCase):
    """FR-12: accepting an Open complaint."""

    def test_open_complaint_becomes_in_progress_and_mine(self) -> None:
        """Accepting moves it to In Progress and assigns it (Confirmation 1)."""
        complaint = self.make_complaint(self.student)
        self.clock_at(30)
        accept_complaint(self.staff, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_IN_PROGRESS)
        self.assertEqual(complaint.assigned_to, self.staff)
        self.assertEqual(complaint.status_changed_at, self.clock.return_value)

    def test_in_progress_complaint_of_another_cannot_be_accepted(self) -> None:
        """The assignment stays unchanged (Confirmation 2)."""
        complaint = self.make_in_progress(self.other_staff)
        with self.assertRaisesMessage(ServiceError, MSG_COMPLAINT_ALREADY_ASSIGNED):
            accept_complaint(self.staff, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.assigned_to, self.other_staff)

    def test_open_complaint_assigned_to_another_cannot_be_accepted(self) -> None:
        """An Open complaint that a supervisor gave to someone else stays theirs."""
        complaint = self.make_complaint(self.student)
        Complaint.objects.filter(pk=complaint.pk).update(assigned_to=self.other_staff)
        with self.assertRaisesMessage(ServiceError, MSG_COMPLAINT_ALREADY_ASSIGNED):
            accept_complaint(self.staff, complaint.complaint_id)

    def test_open_complaint_assigned_to_me_can_be_accepted(self) -> None:
        """An Open complaint already given to me can be accepted by me."""
        complaint = self.make_complaint(self.student)
        Complaint.objects.filter(pk=complaint.pk).update(assigned_to=self.staff)
        accept_complaint(self.staff, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_IN_PROGRESS)

    def test_resolved_or_rejected_complaint_cannot_be_accepted(self) -> None:
        """Only Open complaints can be accepted (Confirmation 3)."""
        resolved = self.make_resolved(self.student, START_TIME)
        rejected = self.make_complaint(self.student)
        reject_complaint(self.staff, rejected.complaint_id, REASON)
        for complaint in (resolved, rejected):
            with self.subTest(status=complaint.status):
                with self.assertRaisesMessage(ServiceError, MSG_ONLY_OPEN_CAN_ACCEPT):
                    accept_complaint(self.staff, complaint.complaint_id)

    def test_unknown_complaint_cannot_be_accepted(self) -> None:
        """A wrong complaint ID gives the "not found" error."""
        with self.assertRaisesMessage(ServiceError, MSG_COMPLAINT_NOT_FOUND):
            accept_complaint(self.staff, UNKNOWN_COMPLAINT_ID)

    def test_only_maintenance_staff_can_accept(self) -> None:
        """Supervisors and complainant roles are refused and nothing changes."""
        complaint = self.make_complaint(self.student)
        for user in (self.supervisor, *self.complainants):
            with self.subTest(role=user.role):
                with self.assertRaisesMessage(ServiceError, MSG_NOT_AUTHORIZED):
                    accept_complaint(user, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)
        self.assertIsNone(complaint.assigned_to)


class ResolveComplaintTests(StaffTestCase):
    """FR-13: marking a complaint as Resolved."""

    def test_assigned_staff_member_resolves_with_time(self) -> None:
        """Status becomes Resolved with the resolution time (Confirmation 1)."""
        complaint = self.make_in_progress(self.staff)
        self.clock_at(60)
        resolve_complaint(self.staff, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)
        self.assertEqual(complaint.resolved_at, self.clock.return_value)
        self.assertEqual(complaint.status_changed_at, self.clock.return_value)

    def test_supervisor_can_resolve_a_complaint_of_staff(self) -> None:
        """A supervisor may resolve any In Progress complaint (Confirmation 1)."""
        complaint = self.make_in_progress(self.staff)
        resolve_complaint(self.supervisor, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)

    def test_open_complaint_must_be_accepted_first(self) -> None:
        """An Open complaint is refused with "accept first" (Confirmation 3)."""
        complaint = self.make_complaint(self.student)
        with self.assertRaisesMessage(ServiceError, MSG_ACCEPT_FIRST):
            resolve_complaint(self.staff, complaint.complaint_id)

    def test_other_staff_member_cannot_resolve(self) -> None:
        """Only the assignee or a supervisor may resolve (Confirmation 4)."""
        complaint = self.make_in_progress(self.other_staff)
        with self.assertRaisesMessage(ServiceError, MSG_ONLY_ASSIGNED_CAN_RESOLVE):
            resolve_complaint(self.staff, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_IN_PROGRESS)

    def test_resolved_or_rejected_complaint_cannot_be_resolved(self) -> None:
        """Only In Progress complaints can be resolved (Confirmation 5)."""
        resolved = self.make_resolved(self.student, START_TIME)
        rejected = self.make_complaint(self.student)
        reject_complaint(self.staff, rejected.complaint_id, REASON)
        for complaint in (resolved, rejected):
            with self.subTest(status=complaint.status):
                with self.assertRaisesMessage(
                    ServiceError, MSG_ONLY_IN_PROGRESS_CAN_RESOLVE
                ):
                    resolve_complaint(self.supervisor, complaint.complaint_id)

    def test_complainant_roles_cannot_resolve(self) -> None:
        """Students, faculty and administrators are refused and nothing changes."""
        complaint = self.make_in_progress(self.staff)
        for user in self.complainants:
            with self.subTest(role=user.role):
                with self.assertRaisesMessage(ServiceError, MSG_NOT_AUTHORIZED):
                    resolve_complaint(user, complaint.complaint_id)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_IN_PROGRESS)


class RejectComplaintTests(StaffTestCase):
    """FR-20: rejecting a complaint with a reason."""

    def assert_rejected_by(self, complaint: Complaint, user: object) -> None:
        """Check that the complaint was rejected with reason, person and time.

        Args:
            complaint: The complaint to reload and check.
            user: Who should have rejected it.
        """
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_REJECTED)
        self.assertEqual(complaint.rejection_reason, REASON)
        self.assertEqual(complaint.rejected_by, user)
        self.assertEqual(complaint.rejected_at, self.clock.return_value)

    def test_open_complaint_can_be_rejected_by_any_staff(self) -> None:
        """Reason, name and time are saved (Confirmation 1)."""
        complaint = self.make_complaint(self.student)
        self.clock_at(15)
        reject_complaint(self.staff, complaint.complaint_id, REASON)
        self.assert_rejected_by(complaint, self.staff)

    def test_assigned_staff_member_rejects_in_progress(self) -> None:
        """The assignee may reject an In Progress complaint (Confirmation 2)."""
        complaint = self.make_in_progress(self.staff)
        reject_complaint(self.staff, complaint.complaint_id, REASON)
        self.assert_rejected_by(complaint, self.staff)

    def test_supervisor_rejects_in_progress_of_staff(self) -> None:
        """A supervisor may reject any In Progress complaint (Confirmation 2)."""
        complaint = self.make_in_progress(self.staff)
        reject_complaint(self.supervisor, complaint.complaint_id, REASON)
        self.assert_rejected_by(complaint, self.supervisor)

    def test_other_staff_member_cannot_reject_in_progress(self) -> None:
        """The complaint stays unchanged (Confirmation 3)."""
        complaint = self.make_in_progress(self.other_staff)
        with self.assertRaisesMessage(ServiceError, MSG_ONLY_ASSIGNED_CAN_REJECT):
            reject_complaint(self.staff, complaint.complaint_id, REASON)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_IN_PROGRESS)
        self.assertEqual(complaint.rejection_reason, "")

    def test_resolved_or_rejected_complaint_cannot_be_rejected(self) -> None:
        """Only Open or In Progress complaints can be rejected (Confirmation 6)."""
        resolved = self.make_resolved(self.student, START_TIME)
        rejected = self.make_complaint(self.student)
        reject_complaint(self.staff, rejected.complaint_id, REASON)
        for complaint in (resolved, rejected):
            with self.subTest(status=complaint.status):
                with self.assertRaisesMessage(ServiceError, MSG_ONLY_ACTIVE_CAN_REJECT):
                    reject_complaint(self.supervisor, complaint.complaint_id, REASON)

    def test_complainant_roles_cannot_reject(self) -> None:
        """Students, faculty and administrators are refused (Confirmation 7)."""
        complaint = self.make_complaint(self.student)
        for user in (self.student, self.administrator):
            with self.subTest(role=user.role):
                with self.assertRaisesMessage(ServiceError, MSG_ONLY_STAFF_CAN_REJECT):
                    reject_complaint(user, complaint.complaint_id, REASON)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)

    def test_unknown_complaint_cannot_be_rejected(self) -> None:
        """A wrong complaint ID gives the "not found" error."""
        with self.assertRaisesMessage(ServiceError, MSG_COMPLAINT_NOT_FOUND):
            reject_complaint(self.staff, UNKNOWN_COMPLAINT_ID, REASON)


class StaffComplaintDetailTests(StaffTestCase):
    """FR-14 location history and the actions offered on a complaint."""

    def test_history_lists_earlier_complaints_at_same_place(self) -> None:
        """Earlier complaints, also Rejected ones, are listed (Confirmation 1)."""
        first = self.make_complaint(self.student, category="plumbing")
        reject_complaint(self.staff, first.complaint_id, REASON)
        self.clock_at(5)
        second = self.make_complaint(self.student)
        self.clock_at(10)
        self.make_complaint(self.student, **OTHER_PLACE)
        self.clock_at(20)
        current = self.make_complaint(self.student)
        self.clock_at(30)
        self.make_complaint(self.student)
        detail = get_staff_complaint_detail(self.staff, current.complaint_id)
        self.assertEqual(detail.location_history, [second, first])

    def test_history_is_empty_without_earlier_complaints(self) -> None:
        """An empty history lets the page show the message (Confirmation 2)."""
        complaint = self.make_complaint(self.student)
        detail = get_staff_complaint_detail(self.staff, complaint.complaint_id)
        self.assertEqual(detail.location_history, [])

    def test_open_complaint_offers_accept_only_to_staff(self) -> None:
        """Staff may accept an Open complaint; a supervisor assigns instead."""
        complaint = self.make_complaint(self.student)
        staff_view = get_staff_complaint_detail(self.staff, complaint.complaint_id)
        supervisor_view = get_staff_complaint_detail(
            self.supervisor, complaint.complaint_id
        )
        self.assertTrue(staff_view.can_accept)
        self.assertFalse(supervisor_view.can_accept)
        self.assertFalse(staff_view.can_resolve)
        self.assertTrue(staff_view.can_reject)

    def test_in_progress_complaint_offers_resolve_and_reject(self) -> None:
        """Resolve and Reject are offered; the service checks the assignee."""
        complaint = self.make_in_progress(self.other_staff)
        detail = get_staff_complaint_detail(self.staff, complaint.complaint_id)
        self.assertFalse(detail.can_accept)
        self.assertTrue(detail.can_resolve)
        self.assertTrue(detail.can_reject)

    def test_rejected_complaint_offers_no_action(self) -> None:
        """A Rejected complaint cannot be changed any more."""
        complaint = self.make_complaint(self.student)
        reject_complaint(self.staff, complaint.complaint_id, REASON)
        detail = get_staff_complaint_detail(self.staff, complaint.complaint_id)
        self.assertFalse(detail.can_accept or detail.can_resolve or detail.can_reject)

    def test_unknown_complaint_is_not_found(self) -> None:
        """A wrong complaint ID gives the "not found" error."""
        with self.assertRaisesMessage(ServiceError, MSG_COMPLAINT_NOT_FOUND):
            get_staff_complaint_detail(self.staff, UNKNOWN_COMPLAINT_ID)
