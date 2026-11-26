"""Tests for the complaint services (FR-06 to FR-10, FR-21)."""

from datetime import datetime, timedelta

from campus.constants import (
    COMPLAINT_IN_PROGRESS,
    COMPLAINT_OPEN,
    COMPLAINT_REJECTED,
    COMPLAINT_RESOLVED,
    MSG_CANNOT_FOLLOW_OWN,
    MSG_COMPLAINT_NOT_ALLOWED,
    MSG_ONLY_BROWSABLE_CAN_FOLLOW,
    MSG_ONLY_RESOLVED_CAN_REOPEN,
    MSG_REOPEN_EXPIRED,
)
from campus.models import Complaint, Follow
from campus.services import (
    BrowseFilters,
    ListedComplaint,
    ServiceError,
    browse_complaints,
    follow_complaint,
    get_complaint_detail,
    get_complaint_photo,
    get_similar_complaints,
    list_my_complaints,
    reopen_complaint,
    unfollow_complaint,
)
from campus.tests.base import START_TIME
from campus.tests.complaint_base import (
    BUILDING,
    FLOOR,
    OTHER_BUILDING,
    OTHER_PLACE,
    PLACE,
    ROOM,
    SECRET_TEXT,
    ComplaintTestCase,
    make_image,
)


class SubmitComplaintTests(ComplaintTestCase):
    """submit_complaint (FR-06, FR-08)."""

    def test_saves_an_open_complaint_with_all_fields(self) -> None:
        """The complaint is saved as Open with the user's input."""
        complaint = self.make_complaint(self.student)
        self.assertEqual(complaint.status, COMPLAINT_OPEN)
        self.assertEqual(complaint.submitted_by, self.student)
        self.assertEqual(complaint.category, "electrical")
        self.assertEqual(complaint.location_label(), f"{BUILDING}, {FLOOR}, {ROOM}")
        self.assertEqual(complaint.description, "The light flickers.")
        self.assertFalse(complaint.is_safety_hazard)

    def test_times_are_set_to_now(self) -> None:
        """Created, opened and last-changed times are all the submit time."""
        complaint = self.make_complaint(self.student)
        self.assertEqual(complaint.created_at, START_TIME)
        self.assertEqual(complaint.opened_at, START_TIME)
        self.assertEqual(complaint.status_changed_at, START_TIME)

    def test_safety_hazard_flag_is_saved(self) -> None:
        """The Safety Hazard flag is stored (FR-08)."""
        complaint = self.make_complaint(self.student, is_safety_hazard=True)
        self.assertTrue(Complaint.objects.get(pk=complaint.pk).is_safety_hazard)

    def test_description_may_be_empty(self) -> None:
        """A complaint without a description is saved."""
        complaint = self.make_complaint(self.student, description="")
        self.assertEqual(complaint.description, "")

    def test_first_id_has_the_year_and_a_padded_number(self) -> None:
        """The first complaint of 2026 is CMP-2026-00001."""
        self.assertEqual(
            self.make_complaint(self.student).complaint_id, "CMP-2026-00001"
        )

    def test_ids_are_unique_and_count_up(self) -> None:
        """Every new complaint gets the next number."""
        ids = [self.make_complaint(self.student).complaint_id for _ in range(12)]
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual(ids[0], "CMP-2026-00001")
        self.assertEqual(ids[-1], "CMP-2026-00012")

    def test_numbering_starts_again_in_a_new_year(self) -> None:
        """The number restarts at 1 when the year changes."""
        self.make_complaint(self.student)
        self.clock.return_value = datetime(2027, 1, 2, 9, 0, tzinfo=START_TIME.tzinfo)
        self.assertEqual(
            self.make_complaint(self.student).complaint_id, "CMP-2027-00001"
        )

    def test_photo_is_stored_under_the_complaint_id(self) -> None:
        """The stored photo is named after the ID, not the user's file name."""
        complaint = self.make_complaint(self.student, photo=make_image("my-pic.PNG"))
        self.assertIn("CMP-2026-00001.png", complaint.photo.name)
        self.assertNotIn("my-pic", complaint.photo.name)

    def test_complaint_without_photo_has_none(self) -> None:
        """No photo means no stored file."""
        self.assertFalse(self.make_complaint(self.student).photo)


class SimilarComplaintTests(ComplaintTestCase):
    """get_similar_complaints (FR-07)."""

    def search(self, **changes: str) -> list[ListedComplaint]:
        """Look for similar complaints as the student.

        Args:
            changes: Search values to replace.

        Returns:
            The similar complaints.
        """
        values = {"category": "electrical", **PLACE}
        values.update(changes)
        return get_similar_complaints(self.student, **values)

    def test_finds_open_complaint_of_another_user(self) -> None:
        """An Open complaint with the same category and place is found."""
        other = self.make_complaint(self.faculty)
        found = self.search()
        self.assertEqual(
            [item.summary.complaint_id for item in found], [other.complaint_id]
        )

    def test_finds_in_progress_complaint(self) -> None:
        """An In Progress complaint is found too."""
        other = self.make_complaint(self.faculty)
        Complaint.objects.filter(pk=other.pk).update(status=COMPLAINT_IN_PROGRESS)
        self.assertEqual(len(self.search()), 1)

    def test_ignores_resolved_and_rejected_complaints(self) -> None:
        """Only Open and In Progress complaints count as already reported."""
        for status in (COMPLAINT_RESOLVED, COMPLAINT_REJECTED):
            other = self.make_complaint(self.faculty)
            Complaint.objects.filter(pk=other.pk).update(status=status)
        self.assertEqual(self.search(), [])

    def test_ignores_other_category_and_other_place(self) -> None:
        """A different category or location is not similar."""
        self.make_complaint(self.faculty, category="plumbing")
        self.make_complaint(
            self.faculty,
            **OTHER_PLACE,
        )
        self.assertEqual(self.search(), [])

    def test_marks_followed_and_own_complaints(self) -> None:
        """The result says which complaints the user follows or owns."""
        followed = self.make_complaint(self.faculty)
        follow_complaint(self.student, followed.complaint_id)
        own = self.make_complaint(self.student)
        marks = {item.summary.complaint_id: item for item in self.search()}
        self.assertTrue(marks[followed.complaint_id].is_following)
        self.assertTrue(marks[own.complaint_id].is_own)

    def test_result_has_no_private_details(self) -> None:
        """The listing cannot carry the description, photo or reporter (FR-07)."""
        self.make_complaint(self.faculty, description=SECRET_TEXT)
        summary = self.search()[0].summary
        for private in ("description", "photo", "submitted_by"):
            self.assertFalse(hasattr(summary, private), private)


class FollowTests(ComplaintTestCase):
    """follow_complaint and unfollow_complaint (FR-07, FR-09)."""

    def setUp(self) -> None:
        """Create one complaint of the faculty member."""
        super().setUp()
        self.complaint = self.make_complaint(self.faculty)

    def test_follow_creates_one_follow(self) -> None:
        """Following saves a Follow for the user."""
        follow_complaint(self.student, self.complaint.complaint_id)
        self.assertTrue(
            Follow.objects.filter(user=self.student, complaint=self.complaint).exists()
        )

    def test_following_twice_changes_nothing(self) -> None:
        """A second follow does not create a second Follow."""
        follow_complaint(self.student, self.complaint.complaint_id)
        follow_complaint(self.student, self.complaint.complaint_id)
        self.assertEqual(Follow.objects.count(), 1)

    def test_follow_does_not_create_a_complaint(self) -> None:
        """Following instead of duplicating adds no new complaint (FR-07)."""
        follow_complaint(self.student, self.complaint.complaint_id)
        self.assertEqual(Complaint.objects.count(), 1)

    def test_cannot_follow_own_complaint(self) -> None:
        """A user cannot follow their own complaint."""
        with self.assertRaises(ServiceError) as caught:
            follow_complaint(self.faculty, self.complaint.complaint_id)
        self.assertEqual(caught.exception.message, MSG_CANNOT_FOLLOW_OWN)

    def test_cannot_follow_unknown_complaint(self) -> None:
        """An ID that does not exist is rejected."""
        with self.assertRaises(ServiceError) as caught:
            follow_complaint(self.student, "CMP-2026-99999")
        self.assertEqual(caught.exception.message, MSG_COMPLAINT_NOT_ALLOWED)

    def test_cannot_follow_resolved_complaint(self) -> None:
        """Only Open and In Progress complaints can be followed."""
        Complaint.objects.filter(pk=self.complaint.pk).update(status=COMPLAINT_RESOLVED)
        with self.assertRaises(ServiceError) as caught:
            follow_complaint(self.student, self.complaint.complaint_id)
        self.assertEqual(caught.exception.message, MSG_ONLY_BROWSABLE_CAN_FOLLOW)

    def test_unfollow_removes_the_follow(self) -> None:
        """Stopping removes the Follow but keeps the complaint."""
        follow_complaint(self.student, self.complaint.complaint_id)
        unfollow_complaint(self.student, self.complaint.complaint_id)
        self.assertEqual(Follow.objects.count(), 0)
        self.assertEqual(Complaint.objects.count(), 1)

    def test_unfollow_without_following_is_harmless(self) -> None:
        """Stopping something that was not followed raises nothing."""
        unfollow_complaint(self.student, self.complaint.complaint_id)
        self.assertEqual(Follow.objects.count(), 0)

    def test_unfollow_only_removes_the_own_follow(self) -> None:
        """Another follower's Follow stays."""
        follow_complaint(self.student, self.complaint.complaint_id)
        follow_complaint(self.administrator, self.complaint.complaint_id)
        unfollow_complaint(self.student, self.complaint.complaint_id)
        self.assertEqual(Follow.objects.get().user, self.administrator)


class MyComplaintsTests(ComplaintTestCase):
    """list_my_complaints (FR-09)."""

    def test_empty_lists_for_a_new_user(self) -> None:
        """A user with no complaints gets two empty lists."""
        result = list_my_complaints(self.student)
        self.assertEqual((result.own, result.following), ([], []))

    def test_own_list_has_only_own_complaints(self) -> None:
        """Another user's complaint is not in the user's own list."""
        mine = self.make_complaint(self.student)
        self.make_complaint(self.faculty)
        self.assertEqual(list_my_complaints(self.student).own, [mine])

    def test_following_list_has_followed_complaints_in_every_status(self) -> None:
        """A followed complaint stays in the list after it is Resolved."""
        other = self.make_complaint(self.faculty)
        follow_complaint(self.student, other.complaint_id)
        Complaint.objects.filter(pk=other.pk).update(status=COMPLAINT_RESOLVED)
        following = list_my_complaints(self.student).following
        self.assertEqual(
            [(item.summary.complaint_id, item.summary.status) for item in following],
            [(other.complaint_id, COMPLAINT_RESOLVED)],
        )

    def test_newest_status_change_comes_first(self) -> None:
        """The list is sorted by the last status change, newest first."""
        older = self.make_complaint(self.student)
        newer = self.make_complaint(self.student)
        Complaint.objects.filter(pk=older.pk).update(
            status_changed_at=START_TIME + timedelta(days=1)
        )
        own = list_my_complaints(self.student).own
        self.assertEqual([c.pk for c in own], [older.pk, newer.pk])


class ComplaintDetailTests(ComplaintTestCase):
    """get_complaint_detail and get_complaint_photo (FR-09, NFR-05)."""

    def test_owner_can_open_the_complaint(self) -> None:
        """The owner gets the complaint."""
        complaint = self.make_complaint(self.student)
        detail = get_complaint_detail(self.student, complaint.complaint_id)
        self.assertEqual(detail.complaint, complaint)

    def test_another_user_is_refused(self) -> None:
        """A user cannot open someone else's complaint."""
        complaint = self.make_complaint(self.student)
        with self.assertRaises(ServiceError) as caught:
            get_complaint_detail(self.faculty, complaint.complaint_id)
        self.assertEqual(caught.exception.message, MSG_COMPLAINT_NOT_ALLOWED)

    def test_unknown_id_gives_the_same_message(self) -> None:
        """A missing ID does not reveal that it does not exist."""
        with self.assertRaises(ServiceError) as caught:
            get_complaint_detail(self.student, "CMP-2026-99999")
        self.assertEqual(caught.exception.message, MSG_COMPLAINT_NOT_ALLOWED)

    def test_open_complaint_cannot_be_reopened(self) -> None:
        """Only a Resolved complaint offers reopening."""
        complaint = self.make_complaint(self.student)
        detail = get_complaint_detail(self.student, complaint.complaint_id)
        self.assertEqual((detail.can_reopen, detail.reopen_expired), (False, False))
        self.assertIsNone(detail.reopen_deadline)

    def test_recent_resolved_complaint_can_be_reopened(self) -> None:
        """A complaint resolved yesterday can be reopened until day 7."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=1))
        detail = get_complaint_detail(self.student, complaint.complaint_id)
        self.assertTrue(detail.can_reopen)
        self.assertEqual(detail.reopen_deadline, START_TIME + timedelta(days=6))

    def test_old_resolved_complaint_is_marked_expired(self) -> None:
        """A complaint resolved 8 days ago can no longer be reopened."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=8))
        detail = get_complaint_detail(self.student, complaint.complaint_id)
        self.assertEqual((detail.can_reopen, detail.reopen_expired), (False, True))

    def test_owner_gets_the_photo(self) -> None:
        """The owner can read the stored photo."""
        complaint = self.make_complaint(self.student, photo=make_image("a.jpg"))
        photo = get_complaint_photo(self.student, complaint.complaint_id)
        self.assertTrue(photo)

    def test_complaint_without_photo_gives_none(self) -> None:
        """No photo gives None."""
        complaint = self.make_complaint(self.student)
        self.assertIsNone(get_complaint_photo(self.student, complaint.complaint_id))

    def test_another_user_cannot_get_the_photo(self) -> None:
        """Photos are only given to the owner."""
        complaint = self.make_complaint(self.student, photo=make_image("a.jpg"))
        with self.assertRaises(ServiceError):
            get_complaint_photo(self.faculty, complaint.complaint_id)


class BrowseComplaintsTests(ComplaintTestCase):
    """browse_complaints (FR-21)."""

    def setUp(self) -> None:
        """Create complaints in different places, categories and statuses."""
        super().setUp()
        self.electrical = self.make_complaint(self.faculty, description=SECRET_TEXT)
        self.plumbing = self.make_complaint(
            self.faculty,
            category="plumbing",
            **OTHER_PLACE,
        )
        self.in_progress = self.make_complaint(self.faculty, category="furniture")
        Complaint.objects.filter(pk=self.in_progress.pk).update(
            status=COMPLAINT_IN_PROGRESS
        )
        self.resolved = self.make_complaint(self.faculty, category="lift")
        Complaint.objects.filter(pk=self.resolved.pk).update(status=COMPLAINT_RESOLVED)

    def ids(self, **filters: str) -> set[str]:
        """Browse with filters and return the IDs found.

        Args:
            filters: Filter values for ``BrowseFilters``.

        Returns:
            The complaint IDs in the result.
        """
        found = browse_complaints(self.student, BrowseFilters(**filters))
        return {item.summary.complaint_id for item in found}

    def test_default_shows_open_and_in_progress_only(self) -> None:
        """Resolved complaints are not listed."""
        self.assertEqual(
            self.ids(),
            {
                self.electrical.complaint_id,
                self.plumbing.complaint_id,
                self.in_progress.complaint_id,
            },
        )

    def test_filter_by_building(self) -> None:
        """Only complaints of that building are listed."""
        self.assertEqual(
            self.ids(building=OTHER_BUILDING), {self.plumbing.complaint_id}
        )

    def test_filter_by_category(self) -> None:
        """Only complaints of that category are listed."""
        self.assertEqual(
            self.ids(category="electrical"), {self.electrical.complaint_id}
        )

    def test_filter_by_status(self) -> None:
        """Only complaints with that status are listed."""
        self.assertEqual(
            self.ids(status=COMPLAINT_IN_PROGRESS), {self.in_progress.complaint_id}
        )

    def test_filters_combine(self) -> None:
        """All filters must match at the same time."""
        self.assertEqual(self.ids(building=BUILDING, category="plumbing"), set())

    def test_no_match_gives_an_empty_list(self) -> None:
        """A filter that nothing matches gives an empty list."""
        self.assertEqual(self.ids(category="wifi"), set())

    def test_resolved_cannot_be_reached_by_a_status_filter(self) -> None:
        """Asking for Resolved still gives nothing (FR-21 shows only active ones)."""
        self.assertEqual(self.ids(status=COMPLAINT_RESOLVED), set())

    def test_items_have_no_private_details(self) -> None:
        """Description, photo and reporter are not part of a listing."""
        summary = browse_complaints(self.student, BrowseFilters())[0].summary
        for private in ("description", "photo", "submitted_by"):
            self.assertFalse(hasattr(summary, private), private)


class ReopenComplaintTests(ComplaintTestCase):
    """reopen_complaint (FR-10)."""

    def resolved_days_ago(self, days: float) -> Complaint:
        """Make the student's complaint, resolved some days before now.

        Args:
            days: How many days ago it was resolved.

        Returns:
            The Resolved complaint.
        """
        return self.make_resolved(self.student, START_TIME - timedelta(days=days))

    def test_reopen_sets_open_and_saves_the_reason(self) -> None:
        """A recently Resolved complaint goes back to Open with the reason."""
        complaint = self.resolved_days_ago(2)
        self.move_clock(timedelta(hours=5))
        reopen_complaint(self.student, complaint.complaint_id, "Still broken.")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)
        self.assertEqual(complaint.reopen_reason, "Still broken.")
        self.assertEqual(complaint.status_changed_at, START_TIME + timedelta(hours=5))
        self.assertEqual(complaint.opened_at, START_TIME + timedelta(hours=5))

    def test_reopen_clears_the_assignment(self) -> None:
        """The previous staff assignment is removed (FR-10)."""
        complaint = self.resolved_days_ago(1)
        Complaint.objects.filter(pk=complaint.pk).update(assigned_to=self.supervisor)
        reopen_complaint(self.student, complaint.complaint_id, "Still broken.")
        complaint.refresh_from_db()
        self.assertIsNone(complaint.assigned_to)

    def test_exactly_seven_days_is_still_allowed(self) -> None:
        """The rule rejects "more than 7 days", so day 7 exactly works."""
        complaint = self.resolved_days_ago(7)
        reopen_complaint(self.student, complaint.complaint_id, "Still broken.")
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)

    def test_one_second_after_seven_days_is_rejected(self) -> None:
        """Just past 7 days the complaint stays Resolved."""
        complaint = self.resolved_days_ago(7)
        self.move_clock(timedelta(seconds=1))
        with self.assertRaises(ServiceError) as caught:
            reopen_complaint(self.student, complaint.complaint_id, "Still broken.")
        self.assertEqual(caught.exception.message, MSG_REOPEN_EXPIRED)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)
        self.assertEqual(complaint.reopen_reason, "")

    def test_resolved_without_a_resolved_time_is_rejected(self) -> None:
        """A Resolved complaint with no resolved time cannot be reopened."""
        complaint = self.resolved_days_ago(1)
        Complaint.objects.filter(pk=complaint.pk).update(resolved_at=None)
        with self.assertRaises(ServiceError) as caught:
            reopen_complaint(self.student, complaint.complaint_id, "Still broken.")
        self.assertEqual(caught.exception.message, MSG_REOPEN_EXPIRED)

    def test_only_resolved_complaints_can_be_reopened(self) -> None:
        """Open, In Progress and Rejected complaints are refused."""
        for status in (COMPLAINT_OPEN, COMPLAINT_IN_PROGRESS, COMPLAINT_REJECTED):
            with self.subTest(status=status):
                complaint = self.make_complaint(self.student)
                Complaint.objects.filter(pk=complaint.pk).update(status=status)
                with self.assertRaises(ServiceError) as caught:
                    reopen_complaint(self.student, complaint.complaint_id, "Why.")
                self.assertEqual(caught.exception.message, MSG_ONLY_RESOLVED_CAN_REOPEN)
                complaint.refresh_from_db()
                self.assertEqual(complaint.status, status)

    def test_another_user_cannot_reopen(self) -> None:
        """Only the owner may reopen a complaint."""
        complaint = self.resolved_days_ago(1)
        with self.assertRaises(ServiceError) as caught:
            reopen_complaint(self.faculty, complaint.complaint_id, "Not mine.")
        self.assertEqual(caught.exception.message, MSG_COMPLAINT_NOT_ALLOWED)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)
