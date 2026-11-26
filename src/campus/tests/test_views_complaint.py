"""Tests for the complaint pages (FR-06 to FR-10, FR-21)."""

from datetime import timedelta
from http import HTTPStatus

from django.urls import reverse

from campus.constants import (
    COMPLAINT_IN_PROGRESS,
    COMPLAINT_OPEN,
    COMPLAINT_RESOLVED,
    MSG_CANNOT_FOLLOW_OWN,
    MSG_COMPLAINT_NOT_ALLOWED,
    MSG_COMPLAINT_NOT_SAVED,
    MSG_COMPLAINT_REOPENED,
    MSG_FOLLOWING_STARTED,
    MSG_FOLLOWING_STOPPED,
    MSG_NO_COMPLAINTS,
    MSG_NO_FILTER_MATCH,
    MSG_NOT_AUTHORIZED,
    MSG_ONLY_RESOLVED_CAN_REOPEN,
    MSG_PHOTO_INVALID,
    MSG_REASON_REQUIRED,
    MSG_REOPEN_EXPIRED,
    MSG_SELECT_CATEGORY,
    MSG_SELECT_LOCATION,
    TEMPLATE_COMPLAINT_DETAIL,
    TEMPLATE_COMPLAINT_SUBMITTED,
    TEMPLATE_EXISTING_COMPLAINTS,
    TEMPLATE_FORBIDDEN,
    TEMPLATE_MY_COMPLAINTS,
    TEMPLATE_REOPEN_COMPLAINT,
    TEMPLATE_SUBMIT_COMPLAINT,
    URL_NAME_COMPLAINT_DETAIL,
    URL_NAME_COMPLAINT_PHOTO,
    URL_NAME_COMPLAINT_SUBMITTED,
    URL_NAME_EXISTING_COMPLAINTS,
    URL_NAME_FOLLOW_COMPLAINT,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_MY_COMPLAINTS,
    URL_NAME_REOPEN_COMPLAINT,
    URL_NAME_SIMILAR_COMPLAINTS,
    URL_NAME_SUBMIT_COMPLAINT,
    URL_NAME_UNFOLLOW_COMPLAINT,
)
from campus.models import Complaint, Follow
from campus.services import follow_complaint
from campus.tests.base import START_TIME
from campus.tests.complaint_base import (
    FIVE_MEGABYTES,
    OTHER_BUILDING,
    OTHER_PLACE,
    PLACE,
    SECRET_TEXT,
    ComplaintTestCase,
    make_image,
)

SUBMIT_URL = reverse(URL_NAME_SUBMIT_COMPLAINT)
SIMILAR_URL = reverse(URL_NAME_SIMILAR_COMPLAINTS)
EXISTING_URL = reverse(URL_NAME_EXISTING_COMPLAINTS)
MY_URL = reverse(URL_NAME_MY_COMPLAINTS)
SOME_ID = "CMP-2026-00001"


def url_for(name: str, complaint_id: str) -> str:
    """Build the address of a complaint page.

    Args:
        name: The URL name.
        complaint_id: The complaint ID.

    Returns:
        The address.
    """
    return reverse(name, kwargs={"complaint_id": complaint_id})


class AccessTests(ComplaintTestCase):
    """Login and role rules for every complaint page."""

    GET_URLS = (
        SUBMIT_URL,
        SIMILAR_URL,
        EXISTING_URL,
        MY_URL,
        url_for(URL_NAME_COMPLAINT_DETAIL, SOME_ID),
        url_for(URL_NAME_COMPLAINT_SUBMITTED, SOME_ID),
        url_for(URL_NAME_COMPLAINT_PHOTO, SOME_ID),
        url_for(URL_NAME_REOPEN_COMPLAINT, SOME_ID),
    )
    POST_URLS = (
        url_for(URL_NAME_FOLLOW_COMPLAINT, SOME_ID),
        url_for(URL_NAME_UNFOLLOW_COMPLAINT, SOME_ID),
    )

    def test_logged_out_user_is_sent_to_login(self) -> None:
        """Every page redirects to the login page without a login."""
        for url in self.GET_URLS + self.POST_URLS:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse(URL_NAME_LOGIN)}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_supervisor_gets_403_everywhere(self) -> None:
        """Only complainants may use the complaint pages (FR-06)."""
        client = self.client_for(self.supervisor)
        for url in self.GET_URLS:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
                self.assertContains(
                    response, MSG_NOT_AUTHORIZED, status_code=HTTPStatus.FORBIDDEN
                )
        for url in self.POST_URLS:
            with self.subTest(url=url):
                self.assertEqual(client.post(url).status_code, HTTPStatus.FORBIDDEN)

    def test_student_faculty_and_administrator_may_submit(self) -> None:
        """All three complainant roles open the form."""
        for user in (self.student, self.faculty, self.administrator):
            with self.subTest(role=user.role):
                response = self.client_for(user).get(SUBMIT_URL)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_follow_and_unfollow_need_post(self) -> None:
        """A GET request cannot follow or unfollow."""
        client = self.client_for(self.student)
        for url in self.POST_URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    client.get(url).status_code, HTTPStatus.METHOD_NOT_ALLOWED
                )

    def test_home_page_links_for_complainants_only(self) -> None:
        """The home page links to the complaint pages for a student only."""
        student_page = self.client_for(self.student).get(reverse(URL_NAME_HOME))
        self.assertContains(student_page, SUBMIT_URL)
        supervisor_page = self.client_for(self.supervisor).get(reverse(URL_NAME_HOME))
        self.assertNotContains(supervisor_page, SUBMIT_URL)


class SubmitComplaintViewTests(ComplaintTestCase):
    """The Submit a complaint page (FR-06, FR-08)."""

    def setUp(self) -> None:
        """Log in as the student."""
        super().setUp()
        self.client = self.client_for(self.student)

    def test_page_shows_the_form(self) -> None:
        """The form has category, location, description, photo and hazard box."""
        response = self.client.get(SUBMIT_URL)
        self.assertTemplateUsed(response, TEMPLATE_SUBMIT_COMPLAINT)
        for text in ("Category", "Location", "Description", "Photo", "Safety Hazard"):
            self.assertContains(response, text)

    def test_valid_submission_saves_and_shows_confirmation(self) -> None:
        """AC: a valid complaint is saved as Open and the ID is shown."""
        response = self.client.post(SUBMIT_URL, self.form_data(), follow=True)
        complaint = Complaint.objects.get()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)
        self.assertEqual(complaint.submitted_by, self.student)
        self.assertRedirects(
            response, url_for(URL_NAME_COMPLAINT_SUBMITTED, complaint.complaint_id)
        )
        self.assertTemplateUsed(response, TEMPLATE_COMPLAINT_SUBMITTED)
        self.assertContains(response, "CMP-2026-00001")

    def test_two_submissions_get_two_different_ids(self) -> None:
        """Every submission gets its own unique ID."""
        self.client.post(SUBMIT_URL, self.form_data())
        self.client.post(SUBMIT_URL, self.form_data())
        ids = list(Complaint.objects.values_list("complaint_id", flat=True))
        self.assertEqual(len(set(ids)), 2)

    def test_safety_hazard_is_saved_and_shown(self) -> None:
        """The flag is saved and shown as text on the confirmation (FR-08)."""
        response = self.client.post(
            SUBMIT_URL, self.form_data(is_safety_hazard="on"), follow=True
        )
        self.assertTrue(Complaint.objects.get().is_safety_hazard)
        self.assertContains(response, "Safety Hazard")

    def test_no_notification_banner_until_notifications_exist(self) -> None:
        """The confirmation does not claim that anyone was notified (FR-05 missing)."""
        response = self.client.post(
            SUBMIT_URL, self.form_data(is_safety_hazard="on"), follow=True
        )
        self.assertNotContains(response, "have been notified")

    def test_missing_category_shows_message_and_saves_nothing(self) -> None:
        """A missing category re-shows the form with the highlighted message."""
        response = self.client.post(SUBMIT_URL, self.form_data(category=None))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, MSG_SELECT_CATEGORY)
        self.assertContains(response, MSG_COMPLAINT_NOT_SAVED)
        self.assertEqual(Complaint.objects.count(), 0)

    def test_missing_location_shows_message_and_saves_nothing(self) -> None:
        """A missing location re-shows the form with the location message."""
        data = self.form_data(building=None, floor=None, room_or_area=None)
        response = self.client.post(SUBMIT_URL, data)
        self.assertContains(response, MSG_SELECT_LOCATION)
        self.assertEqual(Complaint.objects.count(), 0)

    def test_typed_values_are_kept_after_an_error(self) -> None:
        """The description the user typed is still in the form."""
        data = self.form_data(category=None, description="Keep this text")
        self.assertContains(self.client.post(SUBMIT_URL, data), "Keep this text")

    def test_wrong_photo_type_is_rejected(self) -> None:
        """A GIF gives the photo message and saves nothing."""
        photo = make_image("anim.gif")
        response = self.client.post(SUBMIT_URL, self.form_data(photo=photo))
        self.assertContains(response, MSG_PHOTO_INVALID)
        self.assertEqual(Complaint.objects.count(), 0)

    def test_photo_over_five_megabytes_is_rejected(self) -> None:
        """A 5 MB + 1 byte photo gives the photo message."""
        photo = make_image("big.jpg", FIVE_MEGABYTES + 1)
        response = self.client.post(SUBMIT_URL, self.form_data(photo=photo))
        self.assertContains(response, MSG_PHOTO_INVALID)
        self.assertEqual(Complaint.objects.count(), 0)

    def test_valid_photo_is_saved(self) -> None:
        """A JPG within the limit is stored with the complaint."""
        photo = make_image("ok.jpg", 2000)
        self.client.post(SUBMIT_URL, self.form_data(photo=photo))
        self.assertTrue(Complaint.objects.get().photo)

    def test_confirmation_of_someone_elses_complaint_is_refused(self) -> None:
        """Only the owner can open the confirmation page."""
        complaint = self.make_complaint(self.faculty)
        response = self.client.get(
            url_for(URL_NAME_COMPLAINT_SUBMITTED, complaint.complaint_id)
        )
        self.assertContains(
            response, MSG_COMPLAINT_NOT_ALLOWED, status_code=HTTPStatus.FORBIDDEN
        )


class SimilarComplaintsViewTests(ComplaintTestCase):
    """The "Already reported?" panel (FR-07)."""

    def setUp(self) -> None:
        """Log in as the student."""
        super().setUp()
        self.client = self.client_for(self.student)
        self.query = {"category": "electrical", **PLACE}

    def test_without_a_choice_asks_to_select(self) -> None:
        """No category or location gives the "select" hint."""
        response = self.client.get(SIMILAR_URL)
        self.assertContains(response, "Select a category and location")

    def test_match_is_shown_with_a_follow_button(self) -> None:
        """A similar complaint is listed with Follow, without private details."""
        other = self.make_complaint(self.faculty, description=SECRET_TEXT)
        response = self.client.get(SIMILAR_URL, self.query)
        self.assertContains(response, "Electrical")
        self.assertContains(
            response, url_for(URL_NAME_FOLLOW_COMPLAINT, other.complaint_id)
        )
        self.assertNotContains(response, SECRET_TEXT)
        self.assertNotContains(response, self.faculty.username)

    def test_already_followed_complaint_shows_following(self) -> None:
        """A followed complaint shows "Following", not a Follow button."""
        other = self.make_complaint(self.faculty)
        follow_complaint(self.student, other.complaint_id)
        response = self.client.get(SIMILAR_URL, self.query)
        self.assertContains(response, "Following")
        self.assertNotContains(
            response, url_for(URL_NAME_FOLLOW_COMPLAINT, other.complaint_id)
        )

    def test_no_match_says_so(self) -> None:
        """No similar complaint gives a friendly message."""
        response = self.client.get(SIMILAR_URL, self.query)
        self.assertContains(response, "Nothing similar has been reported")

    def test_different_place_is_not_shown(self) -> None:
        """A complaint in another place is not similar."""
        self.make_complaint(
            self.faculty,
            **OTHER_PLACE,
        )
        response = self.client.get(SIMILAR_URL, self.query)
        self.assertContains(response, "Nothing similar has been reported")


class FollowViewTests(ComplaintTestCase):
    """Follow and Stop following (FR-07, FR-09)."""

    def setUp(self) -> None:
        """Log in as the student; the faculty member has a complaint."""
        super().setUp()
        self.client = self.client_for(self.student)
        self.other = self.make_complaint(self.faculty)

    def test_follow_redirects_to_following_tab_with_message(self) -> None:
        """Following shows the Following tab and a success message."""
        url = url_for(URL_NAME_FOLLOW_COMPLAINT, self.other.complaint_id)
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, f"{MY_URL}?tab=following")
        self.assertContains(response, MSG_FOLLOWING_STARTED)
        self.assertTrue(Follow.objects.filter(user=self.student).exists())

    def test_following_own_complaint_shows_the_error(self) -> None:
        """The owner's follow attempt is refused with a message."""
        mine = self.make_complaint(self.student)
        url = url_for(URL_NAME_FOLLOW_COMPLAINT, mine.complaint_id)
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, EXISTING_URL)
        self.assertContains(response, MSG_CANNOT_FOLLOW_OWN)
        self.assertEqual(Follow.objects.count(), 0)

    def test_stop_following_removes_it_from_the_list(self) -> None:
        """Stop following removes the complaint from the Following tab."""
        follow_complaint(self.student, self.other.complaint_id)
        url = url_for(URL_NAME_UNFOLLOW_COMPLAINT, self.other.complaint_id)
        response = self.client.post(url, follow=True)
        self.assertContains(response, MSG_FOLLOWING_STOPPED)
        self.assertContains(response, MSG_NO_COMPLAINTS)
        self.assertEqual(Follow.objects.count(), 0)


class MyComplaintsViewTests(ComplaintTestCase):
    """The My Complaints page (FR-09)."""

    def setUp(self) -> None:
        """Log in as the student."""
        super().setUp()
        self.client = self.client_for(self.student)

    def test_empty_state_message(self) -> None:
        """A user without complaints sees the empty message."""
        response = self.client.get(MY_URL)
        self.assertTemplateUsed(response, TEMPLATE_MY_COMPLAINTS)
        self.assertContains(response, MSG_NO_COMPLAINTS)

    def test_own_complaints_are_listed_with_status_and_flag(self) -> None:
        """The list shows ID, category, location, status and the hazard flag."""
        mine = self.make_complaint(self.student, is_safety_hazard=True)
        response = self.client.get(MY_URL)
        for text in (mine.complaint_id, "Electrical", mine.location_label(), "Open"):
            self.assertContains(response, text)
        self.assertContains(response, "Safety Hazard")
        self.assertContains(
            response, url_for(URL_NAME_COMPLAINT_DETAIL, mine.complaint_id)
        )

    def test_other_users_complaints_are_not_in_my_list(self) -> None:
        """Someone else's complaint never appears in the "My complaints" tab."""
        other = self.make_complaint(self.faculty)
        self.assertNotContains(self.client.get(MY_URL), other.complaint_id)

    def test_following_tab_shows_limited_details(self) -> None:
        """A followed complaint shows category, location and status only."""
        other = self.make_complaint(self.faculty, description=SECRET_TEXT)
        follow_complaint(self.student, other.complaint_id)
        response = self.client.get(MY_URL, {"tab": "following"})
        self.assertContains(response, "Electrical")
        self.assertContains(response, "Stop following")
        self.assertNotContains(response, SECRET_TEXT)
        # The ID is not shown as text; it only appears in the address that the
        # "Stop following" button needs.
        unfollow_url = url_for(URL_NAME_UNFOLLOW_COMPLAINT, other.complaint_id)
        page = response.content.decode().replace(unfollow_url, "")
        self.assertNotIn(other.complaint_id, page)

    def test_resolved_complaint_can_be_opened_to_reopen(self) -> None:
        """A Resolved complaint is listed with its status."""
        resolved = self.make_resolved(self.student, START_TIME)
        self.assertContains(self.client.get(MY_URL), resolved.complaint_id)


class BrowseViewTests(ComplaintTestCase):
    """The Existing Complaints page (FR-21)."""

    def setUp(self) -> None:
        """Log in as the student; add complaints of the faculty member."""
        super().setUp()
        self.client = self.client_for(self.student)

    def test_empty_database_shows_the_empty_message(self) -> None:
        """With no complaints at all the page says so."""
        response = self.client.get(EXISTING_URL)
        self.assertTemplateUsed(response, TEMPLATE_EXISTING_COMPLAINTS)
        self.assertContains(response, MSG_NO_COMPLAINTS)

    def test_lists_complaints_without_private_details(self) -> None:
        """Category, location, status and date are shown; nothing private."""
        other = self.make_complaint(self.faculty, description=SECRET_TEXT)
        response = self.client.get(EXISTING_URL)
        self.assertContains(response, "Electrical")
        self.assertContains(response, other.location_label())
        self.assertContains(response, "Showing 1 complaint")
        self.assertNotContains(response, SECRET_TEXT)
        self.assertNotContains(response, self.faculty.username)

    def test_resolved_complaints_are_hidden(self) -> None:
        """Only Open and In Progress complaints are browsable."""
        self.make_resolved(self.faculty, START_TIME)
        self.assertContains(self.client.get(EXISTING_URL), MSG_NO_COMPLAINTS)

    def test_filters_narrow_the_list(self) -> None:
        """Building, category and status filters all work."""
        self.make_complaint(self.faculty)
        plumbing = self.make_complaint(
            self.faculty,
            category="plumbing",
            **OTHER_PLACE,
        )
        Complaint.objects.filter(pk=plumbing.pk).update(status=COMPLAINT_IN_PROGRESS)
        for query in (
            {"building": OTHER_BUILDING},
            {"category": "plumbing"},
            {"status": COMPLAINT_IN_PROGRESS},
        ):
            with self.subTest(query=query):
                response = self.client.get(EXISTING_URL, query)
                self.assertContains(response, "Showing 1 complaint")
                self.assertContains(response, "Plumbing")

    def test_no_match_message(self) -> None:
        """Filters that match nothing show the no-match message."""
        self.make_complaint(self.faculty)
        response = self.client.get(EXISTING_URL, {"category": "wifi"})
        self.assertContains(response, MSG_NO_FILTER_MATCH)

    def test_invalid_filter_value_is_ignored(self) -> None:
        """A made-up filter value does not break the page."""
        self.make_complaint(self.faculty)
        response = self.client.get(EXISTING_URL, {"status": "resolved"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Showing 1 complaint")

    def test_own_complaint_has_no_follow_button(self) -> None:
        """The user's own complaint is marked, not followable."""
        mine = self.make_complaint(self.student)
        response = self.client.get(EXISTING_URL)
        self.assertContains(response, "Your complaint")
        self.assertNotContains(
            response, url_for(URL_NAME_FOLLOW_COMPLAINT, mine.complaint_id)
        )


class DetailViewTests(ComplaintTestCase):
    """The complaint detail page and its photo (FR-09, NFR-05)."""

    def setUp(self) -> None:
        """Log in as the student, who has a complaint with a photo."""
        super().setUp()
        self.client = self.client_for(self.student)
        self.mine = self.make_complaint(
            self.student, description=SECRET_TEXT, photo=make_image("a.jpg")
        )
        self.url = url_for(URL_NAME_COMPLAINT_DETAIL, self.mine.complaint_id)

    def test_owner_sees_all_details(self) -> None:
        """The owner sees the description and the photo."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, TEMPLATE_COMPLAINT_DETAIL)
        self.assertContains(response, SECRET_TEXT)
        self.assertContains(
            response, url_for(URL_NAME_COMPLAINT_PHOTO, self.mine.complaint_id)
        )

    def test_another_user_gets_403_with_the_message(self) -> None:
        """A user cannot open another user's complaint."""
        response = self.client_for(self.faculty).get(self.url)
        self.assertTemplateUsed(response, TEMPLATE_FORBIDDEN)
        self.assertContains(
            response, MSG_COMPLAINT_NOT_ALLOWED, status_code=HTTPStatus.FORBIDDEN
        )
        self.assertNotContains(response, SECRET_TEXT, status_code=HTTPStatus.FORBIDDEN)

    def test_unknown_id_looks_the_same(self) -> None:
        """A missing complaint gives the same 403 as someone else's."""
        response = self.client.get(url_for(URL_NAME_COMPLAINT_DETAIL, "CMP-2026-99999"))
        self.assertContains(
            response, MSG_COMPLAINT_NOT_ALLOWED, status_code=HTTPStatus.FORBIDDEN
        )

    def test_owner_gets_the_photo_file(self) -> None:
        """The photo address returns the image to the owner."""
        response = self.client.get(
            url_for(URL_NAME_COMPLAINT_PHOTO, self.mine.complaint_id)
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertTrue(
            b"".join(response.streaming_content).startswith(b"\xff\xd8\xff")
        )

    def test_another_user_cannot_get_the_photo(self) -> None:
        """Photos are not shared with other users (NFR-05)."""
        response = self.client_for(self.faculty).get(
            url_for(URL_NAME_COMPLAINT_PHOTO, self.mine.complaint_id)
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_complaint_without_photo_gives_404(self) -> None:
        """A complaint with no photo has nothing to send."""
        other = self.make_complaint(self.student)
        response = self.client.get(
            url_for(URL_NAME_COMPLAINT_PHOTO, other.complaint_id)
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class MissingPhotoFileTests(ComplaintTestCase):
    """A photo that is saved in the database but gone from the disk."""

    def test_missing_file_gives_404_not_an_error_page(self) -> None:
        """The photo address answers 404 when the stored file was deleted."""
        complaint = self.make_complaint(self.student, photo=make_image("a.jpg"))
        complaint.photo.delete(save=False)
        Complaint.objects.filter(pk=complaint.pk).update(photo="complaint_photos/x.jpg")
        response = self.client_for(self.student).get(
            url_for(URL_NAME_COMPLAINT_PHOTO, complaint.complaint_id)
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class ReopenViewTests(ComplaintTestCase):
    """The Reopen page and the 7-day rule (FR-10)."""

    def setUp(self) -> None:
        """Log in as the student."""
        super().setUp()
        self.client = self.client_for(self.student)

    def reopen_url(self, complaint: Complaint) -> str:
        """Build the reopen address of a complaint.

        Args:
            complaint: The complaint.

        Returns:
            The address.
        """
        return url_for(URL_NAME_REOPEN_COMPLAINT, complaint.complaint_id)

    def detail_url(self, complaint: Complaint) -> str:
        """Build the detail address of a complaint.

        Args:
            complaint: The complaint.

        Returns:
            The address.
        """
        return url_for(URL_NAME_COMPLAINT_DETAIL, complaint.complaint_id)

    def test_detail_offers_reopen_for_recent_resolved_complaint(self) -> None:
        """Within 7 days the detail page shows the Reopen button."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=2))
        response = self.client.get(self.detail_url(complaint))
        self.assertContains(response, self.reopen_url(complaint))
        self.assertNotContains(response, MSG_REOPEN_EXPIRED)

    def test_detail_explains_when_the_window_has_passed(self) -> None:
        """After 7 days the page shows the message and no Reopen button."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=8))
        response = self.client.get(self.detail_url(complaint))
        self.assertContains(response, MSG_REOPEN_EXPIRED)
        self.assertNotContains(response, self.reopen_url(complaint))

    def test_open_complaint_shows_no_reopen_option(self) -> None:
        """An Open complaint has no Reopen button and no expiry message."""
        complaint = self.make_complaint(self.student)
        response = self.client.get(self.detail_url(complaint))
        self.assertNotContains(response, self.reopen_url(complaint))
        self.assertNotContains(response, MSG_REOPEN_EXPIRED)

    def test_reopen_page_shows_the_reason_form(self) -> None:
        """The reopen page asks for a reason."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=1))
        response = self.client.get(self.reopen_url(complaint))
        self.assertTemplateUsed(response, TEMPLATE_REOPEN_COMPLAINT)
        self.assertContains(response, "Reason")

    def test_successful_reopen(self) -> None:
        """A reason reopens the complaint and shows a success message."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=1))
        response = self.client.post(
            self.reopen_url(complaint), {"reason": "Still broken."}, follow=True
        )
        self.assertRedirects(response, self.detail_url(complaint))
        self.assertContains(response, MSG_COMPLAINT_REOPENED)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)
        self.assertEqual(complaint.reopen_reason, "Still broken.")

    def test_reopen_without_reason_shows_the_message(self) -> None:
        """An empty reason shows "Please enter a reason." and changes nothing."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=1))
        response = self.client.post(self.reopen_url(complaint), {"reason": ""})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, MSG_REASON_REQUIRED)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)

    def test_reopen_after_seven_days_is_refused(self) -> None:
        """A direct POST after 7 days is refused with the expiry message."""
        complaint = self.make_resolved(self.student, START_TIME - timedelta(days=8))
        response = self.client.post(
            self.reopen_url(complaint), {"reason": "Still broken."}, follow=True
        )
        self.assertContains(response, MSG_REOPEN_EXPIRED)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)

    def test_reopen_of_a_complaint_that_is_not_resolved_is_refused(self) -> None:
        """A direct POST for an Open complaint gives the Resolved-only message."""
        complaint = self.make_complaint(self.student)
        response = self.client.post(
            self.reopen_url(complaint), {"reason": "Why not."}, follow=True
        )
        self.assertContains(response, MSG_ONLY_RESOLVED_CAN_REOPEN)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_OPEN)

    def test_reopen_page_of_an_open_complaint_goes_back_to_detail(self) -> None:
        """The reopen form is not shown for a complaint that cannot be reopened."""
        complaint = self.make_complaint(self.student)
        response = self.client.get(self.reopen_url(complaint))
        self.assertRedirects(response, self.detail_url(complaint))

    def test_another_user_cannot_reopen(self) -> None:
        """Another user's POST gets the 403 page and changes nothing."""
        complaint = self.make_resolved(self.faculty, START_TIME - timedelta(days=1))
        response = self.client.post(self.reopen_url(complaint), {"reason": "Mine now."})
        self.assertContains(
            response, MSG_COMPLAINT_NOT_ALLOWED, status_code=HTTPStatus.FORBIDDEN
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_RESOLVED)

    def test_another_user_cannot_open_the_reopen_page(self) -> None:
        """The reopen page of someone else's complaint is a 403."""
        complaint = self.make_resolved(self.faculty, START_TIME - timedelta(days=1))
        response = self.client.get(self.reopen_url(complaint))
        self.assertContains(
            response, MSG_COMPLAINT_NOT_ALLOWED, status_code=HTTPStatus.FORBIDDEN
        )
