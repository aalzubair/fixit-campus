"""Tests for the staff pages (F5: FR-11 to FR-14, FR-20)."""

from http import HTTPStatus

from django.urls import reverse

from campus.constants import (
    COMPLAINT_IN_PROGRESS,
    COMPLAINT_REJECTED,
    MSG_ACCEPT_FIRST,
    MSG_COMPLAINT_ACCEPTED,
    MSG_COMPLAINT_REJECTED,
    MSG_COMPLAINT_RESOLVED,
    MSG_NO_COMPLAINT_HISTORY,
    MSG_NO_COMPLAINTS,
    MSG_NO_FILTER_MATCH,
    MSG_NOT_AUTHORIZED,
    MSG_ONLY_ASSIGNED_CAN_RESOLVE,
    MSG_ONLY_STAFF_CAN_REJECT,
    MSG_REASON_REQUIRED,
    URL_NAME_ACCEPT_COMPLAINT,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_REJECT_COMPLAINT,
    URL_NAME_RESOLVE_COMPLAINT,
    URL_NAME_STAFF_COMPLAINT_DETAIL,
    URL_NAME_STAFF_COMPLAINTS,
)
from campus.tests.staff_base import StaffTestCase

UNKNOWN_COMPLAINT_ID = "CMP-2026-99999"


def complaint_url(name: str, complaint_id: str) -> str:
    """Build the address of a staff page of one complaint.

    Args:
        name: The URL name constant.
        complaint_id: The complaint ID.

    Returns:
        The address.
    """
    return reverse(name, args=(complaint_id,))


class StaffListViewTests(StaffTestCase):
    """FR-11: who may open the list and what it shows."""

    def setUp(self) -> None:
        """Remember the list address."""
        super().setUp()
        self.url = reverse(URL_NAME_STAFF_COMPLAINTS)

    def test_staff_and_supervisor_can_open_the_list(self) -> None:
        """Both staff roles see the list with the complaint ID."""
        complaint = self.make_complaint(self.student)
        for user in (self.staff, self.supervisor):
            with self.subTest(role=user.role):
                response = self.client_for(user).get(self.url)
                self.assertContains(response, complaint.complaint_id)

    def test_complainant_is_refused(self) -> None:
        """A student gets the "not authorized" page."""
        response = self.client_for(self.student).get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertContains(
            response, MSG_NOT_AUTHORIZED, status_code=HTTPStatus.FORBIDDEN
        )

    def test_anonymous_user_goes_to_login(self) -> None:
        """Without logging in, the list redirects to the login page."""
        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse(URL_NAME_LOGIN)}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_empty_list_and_no_match_messages(self) -> None:
        """No complaints and no matching complaints show their own messages."""
        client = self.client_for(self.staff)
        self.assertContains(client.get(self.url), MSG_NO_COMPLAINTS)
        self.make_complaint(self.student)
        response = client.get(self.url, {"status": COMPLAINT_REJECTED})
        self.assertContains(response, MSG_NO_FILTER_MATCH)

    def test_accept_button_only_for_staff(self) -> None:
        """Staff can accept from the list; a supervisor cannot."""
        complaint = self.make_complaint(self.student)
        accept_url = complaint_url(URL_NAME_ACCEPT_COMPLAINT, complaint.complaint_id)
        self.assertContains(self.client_for(self.staff).get(self.url), accept_url)
        self.assertNotContains(
            self.client_for(self.supervisor).get(self.url), accept_url
        )

    def test_home_page_links_to_the_list_for_staff(self) -> None:
        """The staff home page offers the complaint list."""
        response = self.client_for(self.staff).get(reverse(URL_NAME_HOME))
        self.assertContains(response, self.url)


class StaffDetailViewTests(StaffTestCase):
    """FR-14 and the detail page."""

    def test_detail_shows_empty_history_message(self) -> None:
        """Without earlier complaints, the history message is shown."""
        complaint = self.make_complaint(self.student)
        url = complaint_url(URL_NAME_STAFF_COMPLAINT_DETAIL, complaint.complaint_id)
        response = self.client_for(self.staff).get(url)
        self.assertContains(response, MSG_NO_COMPLAINT_HISTORY)

    def test_detail_lists_earlier_complaint(self) -> None:
        """An earlier complaint at the same place is listed."""
        earlier = self.make_complaint(self.student)
        self.clock_at(5)
        current = self.make_complaint(self.student)
        url = complaint_url(URL_NAME_STAFF_COMPLAINT_DETAIL, current.complaint_id)
        response = self.client_for(self.staff).get(url)
        self.assertContains(response, earlier.complaint_id)
        self.assertNotContains(response, MSG_NO_COMPLAINT_HISTORY)

    def test_staff_names_are_shown_instead_of_id_numbers(self) -> None:
        """Assigned to and Rejected by show the member's name (CR-03)."""
        self.assertTrue(self.staff.get_full_name())
        in_progress = self.make_in_progress(self.staff)
        rejected = self.make_complaint(self.student)
        self.client_for(self.supervisor).post(
            complaint_url(URL_NAME_REJECT_COMPLAINT, rejected.complaint_id),
            {"reason": "Not a maintenance issue."},
        )
        client = self.client_for(self.other_staff)
        pages = (
            reverse(URL_NAME_STAFF_COMPLAINTS),
            complaint_url(URL_NAME_STAFF_COMPLAINT_DETAIL, in_progress.complaint_id),
        )
        for url in pages:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertContains(response, self.staff.get_full_name())
                self.assertNotContains(response, self.staff.username)
        rejected_page = client.get(
            complaint_url(URL_NAME_STAFF_COMPLAINT_DETAIL, rejected.complaint_id)
        )
        self.assertContains(rejected_page, self.supervisor.get_full_name())

    def test_unknown_complaint_gives_404(self) -> None:
        """A wrong complaint ID is "not found"."""
        url = complaint_url(URL_NAME_STAFF_COMPLAINT_DETAIL, UNKNOWN_COMPLAINT_ID)
        response = self.client_for(self.staff).get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class StaffActionViewTests(StaffTestCase):
    """FR-12 and FR-13 through the pages."""

    def test_accept_redirects_with_success_message(self) -> None:
        """Accepting goes back to the complaint and confirms it."""
        complaint = self.make_complaint(self.student)
        url = complaint_url(URL_NAME_ACCEPT_COMPLAINT, complaint.complaint_id)
        response = self.client_for(self.staff).post(url, follow=True)
        self.assertContains(response, MSG_COMPLAINT_ACCEPTED)

    def test_accept_needs_post(self) -> None:
        """Opening the accept address in the browser changes nothing."""
        complaint = self.make_complaint(self.student)
        url = complaint_url(URL_NAME_ACCEPT_COMPLAINT, complaint.complaint_id)
        response = self.client_for(self.staff).get(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_supervisor_cannot_accept(self) -> None:
        """Accepting is for maintenance staff only (UC-12)."""
        complaint = self.make_complaint(self.student)
        url = complaint_url(URL_NAME_ACCEPT_COMPLAINT, complaint.complaint_id)
        response = self.client_for(self.supervisor).post(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_resolve_shows_success_message(self) -> None:
        """Resolving goes back to the complaint and confirms it."""
        complaint = self.make_in_progress(self.staff)
        url = complaint_url(URL_NAME_RESOLVE_COMPLAINT, complaint.complaint_id)
        response = self.client_for(self.staff).post(url, follow=True)
        self.assertContains(response, MSG_COMPLAINT_RESOLVED)

    def test_resolve_errors_show_the_srs_messages(self) -> None:
        """Refused actions show the SRS message on the complaint page."""
        open_complaint = self.make_complaint(self.student)
        colleague_complaint = self.make_in_progress(self.other_staff)
        cases = (
            (open_complaint, MSG_ACCEPT_FIRST),
            (colleague_complaint, MSG_ONLY_ASSIGNED_CAN_RESOLVE),
        )
        client = self.client_for(self.staff)
        for complaint, message in cases:
            with self.subTest(message=message):
                url = complaint_url(URL_NAME_RESOLVE_COMPLAINT, complaint.complaint_id)
                self.assertContains(client.post(url, follow=True), message)

    def test_complainant_roles_get_403_on_accept_and_resolve(self) -> None:
        """Students, faculty and administrators are refused and nothing changes."""
        complaint = self.make_in_progress(self.staff)
        for name in (URL_NAME_ACCEPT_COMPLAINT, URL_NAME_RESOLVE_COMPLAINT):
            url = complaint_url(name, complaint.complaint_id)
            for user in self.complainants:
                with self.subTest(action=name, role=user.role):
                    response = self.client_for(user).post(url)
                    self.assertContains(
                        response, MSG_NOT_AUTHORIZED, status_code=HTTPStatus.FORBIDDEN
                    )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, COMPLAINT_IN_PROGRESS)

    def test_anonymous_user_posting_goes_to_login(self) -> None:
        """Without logging in, accept and resolve redirect to the login page."""
        complaint = self.make_complaint(self.student)
        for name in (URL_NAME_ACCEPT_COMPLAINT, URL_NAME_RESOLVE_COMPLAINT):
            url = complaint_url(name, complaint.complaint_id)
            with self.subTest(action=name):
                self.assertRedirects(
                    self.client.post(url),
                    f"{reverse(URL_NAME_LOGIN)}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_unknown_complaint_action_gives_404(self) -> None:
        """Acting on a wrong complaint ID is "not found"."""
        url = complaint_url(URL_NAME_RESOLVE_COMPLAINT, UNKNOWN_COMPLAINT_ID)
        response = self.client_for(self.staff).post(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class RejectViewTests(StaffTestCase):
    """FR-20 through the reject page."""

    def setUp(self) -> None:
        """Submit one Open complaint and remember its reject address."""
        super().setUp()
        self.complaint = self.make_complaint(self.student)
        self.url = complaint_url(URL_NAME_REJECT_COMPLAINT, self.complaint.complaint_id)

    def test_reject_page_shows_the_form(self) -> None:
        """Staff see the reason form."""
        response = self.client_for(self.staff).get(self.url)
        self.assertContains(response, "Reason for rejecting")

    def test_missing_reason_shows_message(self) -> None:
        """Without a reason nothing changes (Confirmation 5)."""
        response = self.client_for(self.staff).post(self.url, {"reason": ""})
        self.assertContains(response, MSG_REASON_REQUIRED)
        self.complaint.refresh_from_db()
        self.assertNotEqual(self.complaint.status, COMPLAINT_REJECTED)

    def test_reason_rejects_and_confirms(self) -> None:
        """With a reason the complaint is rejected (Confirmation 1)."""
        response = self.client_for(self.staff).post(
            self.url, {"reason": "Not a maintenance issue."}, follow=True
        )
        self.assertContains(response, MSG_COMPLAINT_REJECTED)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, COMPLAINT_REJECTED)

    def test_complainant_gets_the_fr20_message(self) -> None:
        """A student is denied with the FR-20 message (Confirmation 7)."""
        response = self.client_for(self.student).get(self.url)
        self.assertContains(
            response, MSG_ONLY_STAFF_CAN_REJECT, status_code=HTTPStatus.FORBIDDEN
        )

    def test_unknown_complaint_gives_404(self) -> None:
        """The reject page of a wrong complaint ID is "not found"."""
        url = complaint_url(URL_NAME_REJECT_COMPLAINT, UNKNOWN_COMPLAINT_ID)
        response = self.client_for(self.staff).get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
