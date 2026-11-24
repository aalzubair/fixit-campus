"""Tests for the FR-02 and FR-03 pages: log in, home, log out, idle timeout, roles.

Acceptance criteria (AC) numbers refer to SRS FR-02 and FR-03 Confirmations.
"""

import re
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse

from campus.constants import (
    ACCOUNT_LOCK_MINUTES,
    HOME_PAGE_TEXT,
    MSG_ACCOUNT_LOCKED,
    MSG_ACCOUNT_NO_LONGER_ACTIVE,
    MSG_INVALID_LOGIN,
    MSG_NOT_AUTHORIZED,
    MSG_SESSION_EXPIRED,
    ROLE_ADMINISTRATOR,
    ROLE_CHOICES,
    ROLE_FACULTY,
    ROLE_STUDENT,
    SESSION_IDLE_TIMEOUT_MINUTES,
    TEMPLATE_FORBIDDEN,
    TEMPLATE_HOME,
    TEMPLATE_LOGIN,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_LOGOUT,
    URL_NAME_PASSWORD_RESET,
    URL_NAME_REGISTER,
)
from campus.models import User
from campus.services import request_password_reset, reset_password
from campus.tests.base import (
    ADMINISTRATOR_ID,
    FACULTY_ID,
    GOOD_PASSWORD,
    MOBILE_ONLY_ID,
    NEW_PASSWORD,
    STUDENT_ID,
    STUDENT_NAME,
    SUPERVISOR_ID,
    UNKNOWN_ID,
    WRONG_PASSWORD,
    RegistrationTestCase,
)
from campus.views import role_required

LOGIN_URL = reverse(URL_NAME_LOGIN)
LOGOUT_URL = reverse(URL_NAME_LOGOUT)
HOME_URL = reverse(URL_NAME_HOME)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "campus"
ONE_SECOND = timedelta(seconds=1)
IDLE_TIMEOUT = timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES)
HEADING_BY_ROLE = {role: heading for role, heading, _ in HOME_PAGE_TEXT}
CSRF_FIELD = 'name="csrfmiddlewaretoken"'
CSRF_VALUE_PATTERN = CSRF_FIELD + r' value="[^"]*"'
BFCACHE_SCRIPT = 'id="bfcache-reload"'
STUDENT_ROLE_LABEL = dict(ROLE_CHOICES)[ROLE_STUDENT]


@role_required(ROLE_ADMINISTRATOR)
def admin_only_view(request: HttpRequest) -> HttpResponse:
    """A tiny administrator-only view used only by these tests (no URL route).

    Args:
        request: The HTTP request.

    Returns:
        A plain "ok" page.
    """
    return HttpResponse(f"ok {request.user}")


def page_without_id_and_token(response: HttpResponse, id_number: str) -> str:
    """Remove the typed ID and the CSRF token, which differ on every page.

    Args:
        response: A rendered login page.
        id_number: The ID that was typed into the form.

    Returns:
        The page text without the ID and the token value.
    """
    page = response.content.decode().replace(id_number, "")
    return re.sub(CSRF_VALUE_PATTERN, "", page)


class AuthPageTestCase(RegistrationTestCase):
    """Base class: an active student and a login helper."""

    def setUp(self) -> None:
        """Create an active student."""
        super().setUp()
        self.make_active_user(STUDENT_ID)

    def post_login(self, id_number: str, password: str) -> HttpResponse:
        """Submit the login form.

        Args:
            id_number: The IUB ID number to submit.
            password: The password to submit.

        Returns:
            The test client response.
        """
        return self.client.post(
            LOGIN_URL, {"id_number": id_number, "password": password}
        )

    def assert_logged_in(self) -> None:
        """Check that the home page is shown, not a redirect to login."""
        self.assertEqual(self.client.get(HOME_URL).status_code, HTTPStatus.OK)

    def assert_logged_out(self) -> None:
        """Check that the home page redirects to the login page."""
        response = self.client.get(HOME_URL)
        self.assertRedirects(response, f"{LOGIN_URL}?next={HOME_URL}")


class LoginPageTests(AuthPageTestCase):
    """The /login/ page (FR-02)."""

    def test_page_shows_form_and_links(self) -> None:
        """The page has the form, "Forgot password?" and "Register"."""
        response = self.client.get(LOGIN_URL)
        self.assertTemplateUsed(response, TEMPLATE_LOGIN)
        self.assertContains(response, "Forgot password?")
        self.assertContains(response, reverse(URL_NAME_PASSWORD_RESET))
        self.assertContains(response, reverse(URL_NAME_REGISTER))

    def test_correct_login_goes_to_home_page(self) -> None:
        """AC 1: the correct ID and password open the home page."""
        response = self.post_login(STUDENT_ID, GOOD_PASSWORD)
        self.assertRedirects(response, HOME_URL)
        self.assert_logged_in()

    def test_each_role_sees_its_own_home_page(self) -> None:
        """AC 1: the home page heading matches the user's role."""
        for id_number in (FACULTY_ID, MOBILE_ONLY_ID, SUPERVISOR_ID, ADMINISTRATOR_ID):
            with self.subTest(id_number=id_number):
                user = self.make_active_user(id_number)
                self.client.force_login(user)
                response = self.client.get(HOME_URL)
                self.assertTemplateUsed(response, TEMPLATE_HOME)
                self.assertContains(response, HEADING_BY_ROLE[user.role])

    def test_wrong_password_shows_generic_message(self) -> None:
        """AC 2: a wrong password shows "Invalid ID or password"."""
        response = self.post_login(STUDENT_ID, WRONG_PASSWORD)
        self.assertContains(response, MSG_INVALID_LOGIN)
        self.assert_logged_out()

    def test_unknown_id_shows_same_page_as_wrong_password(self) -> None:
        """The page never shows whether an ID exists."""
        wrong_password_page = self.post_login(STUDENT_ID, WRONG_PASSWORD)
        unknown_id_page = self.post_login(UNKNOWN_ID, WRONG_PASSWORD)
        self.assertContains(unknown_id_page, MSG_INVALID_LOGIN)
        self.assertEqual(
            page_without_id_and_token(wrong_password_page, STUDENT_ID),
            page_without_id_and_token(unknown_id_page, UNKNOWN_ID),
        )

    def test_wrong_three_character_password_counts_as_failed_attempt(self) -> None:
        """The form has no length rule, so a short password reaches the service."""
        response = self.post_login(STUDENT_ID, "abc")
        self.assertContains(response, MSG_INVALID_LOGIN)
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.failed_login_attempts, 1)

    def test_empty_fields_show_required_errors_and_count_nothing(self) -> None:
        """Empty ID or password is stopped by the form."""
        response = self.post_login("", "")
        self.assertEqual(
            response.context["form"].errors.keys(), {"id_number", "password"}
        )
        user = User.objects.get(username=STUDENT_ID)
        self.assertEqual(user.failed_login_attempts, 0)

    def test_empty_password_shows_required_error(self) -> None:
        """An empty password is stopped by the form."""
        response = self.post_login(STUDENT_ID, "")
        self.assertEqual(response.context["form"].errors.keys(), {"password"})

    def test_locked_account_shows_locked_message(self) -> None:
        """AC 3 and 5: after 5 wrong passwords even the right one is refused."""
        self.type_wrong_passwords(STUDENT_ID)
        response = self.post_login(STUDENT_ID, GOOD_PASSWORD)
        self.assertContains(response, MSG_ACCOUNT_LOCKED)
        self.assert_logged_out()

    def test_lock_ended_allows_login(self) -> None:
        """AC 6: 15 minutes after the lock the user can log in."""
        self.type_wrong_passwords(STUDENT_ID)
        self.move_clock(timedelta(minutes=ACCOUNT_LOCK_MINUTES))
        self.assertRedirects(self.post_login(STUDENT_ID, GOOD_PASSWORD), HOME_URL)

    def test_member_no_longer_in_records_shows_message(self) -> None:
        """AC 7: a member who left the university is refused."""
        self.records.remove_member(STUDENT_ID)
        response = self.post_login(STUDENT_ID, GOOD_PASSWORD)
        self.assertContains(response, MSG_ACCOUNT_NO_LONGER_ACTIVE)
        self.assert_logged_out()

    def test_changed_role_shows_current_home_page(self) -> None:
        """AC 8: a role changed in the records shows the new home page."""
        self.records.change_member(STUDENT_ID, role=ROLE_FACULTY)
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.get(HOME_URL)
        self.assertContains(response, HEADING_BY_ROLE[ROLE_FACULTY])
        self.assertNotContains(response, HEADING_BY_ROLE[ROLE_STUDENT])

    def test_logged_in_user_is_sent_from_login_to_home(self) -> None:
        """A logged-in user who opens /login/ goes to the home page."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        self.assertRedirects(self.client.get(LOGIN_URL), HOME_URL)

    def test_old_password_rejected_after_reset(self) -> None:
        """FR-04 AC 7 through the login page."""
        request_password_reset(STUDENT_ID)
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        self.assertContains(
            self.post_login(STUDENT_ID, GOOD_PASSWORD), MSG_INVALID_LOGIN
        )
        self.assertRedirects(self.post_login(STUDENT_ID, NEW_PASSWORD), HOME_URL)


class NavbarTests(AuthPageTestCase):
    """The navbar in base.html."""

    def test_logged_out_navbar_shows_log_in_and_register(self) -> None:
        """Logged out: "Log in" and "Register", no "Log out"."""
        response = self.client.get(LOGIN_URL)
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")
        self.assertNotContains(response, "Log out")

    def test_logged_in_navbar_shows_name_role_and_log_out(self) -> None:
        """Logged in: the full name, the role name and a "Log out" button."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.get(HOME_URL)
        self.assertContains(response, f"{STUDENT_NAME} · {STUDENT_ROLE_LABEL}")
        self.assertNotContains(response, STUDENT_ID)
        self.assertContains(response, "Log out")
        self.assertContains(response, f'action="{LOGOUT_URL}"')

    def test_navbar_shows_id_when_user_has_no_name(self) -> None:
        """An account saved before names were copied shows the ID instead."""
        User.objects.filter(username=STUDENT_ID).update(first_name="")
        self.client.force_login(User.objects.get(username=STUDENT_ID))
        response = self.client.get(HOME_URL)
        self.assertContains(response, f"{STUDENT_ID} · {STUDENT_ROLE_LABEL}")
        self.assertNotContains(response, STUDENT_NAME)


class LogoutTests(AuthPageTestCase):
    """Log out and protected pages (FR-03)."""

    def test_logout_ends_session_and_shows_login_page(self) -> None:
        """FR-03 AC 1: after log out the login page is shown."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.post(LOGOUT_URL)
        self.assertRedirects(response, LOGIN_URL)
        self.assert_logged_out()

    def test_logout_with_get_is_not_allowed(self) -> None:
        """Log out is POST only, and a GET keeps the user logged in."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assert_logged_in()

    def test_protected_page_after_logout_asks_to_log_in(self) -> None:
        """FR-03 AC 2: the address of a protected page goes to login."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        self.client.post(LOGOUT_URL)
        self.assert_logged_out()

    def test_home_page_is_never_cached(self) -> None:
        """FR-03 AC 2: the back button cannot show a cached home page."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.get(HOME_URL)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_old_session_ends_after_password_reset(self) -> None:
        """A session started before a password reset no longer works."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        request_password_reset(STUDENT_ID)
        reset_password(STUDENT_ID, self.sender.last_code, NEW_PASSWORD)
        self.assert_logged_out()


class BackForwardCacheTests(AuthPageTestCase):
    """FR-03 AC 2: the Back button after Log out must not show an old page.

    Two defences: no-cache headers stop normal caching, and a small script
    in logged-in pages reloads a page restored from the browser's
    back-forward cache. These tests check that both are sent. Whether a
    real browser runs the script on Back cannot be tested without a
    browser; that part is checked by hand.
    """

    def test_logged_in_page_has_reload_script(self) -> None:
        """Pages rendered for a logged-in user carry the reload script."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.get(HOME_URL)
        self.assertContains(response, BFCACHE_SCRIPT)
        self.assertContains(response, "event.persisted")

    def test_403_page_has_reload_script(self) -> None:
        """The access-denied page is also a logged-in page."""
        request = RequestFactory().get("/test-only/")
        request.user = User.objects.get(username=STUDENT_ID)
        response = admin_only_view(request)
        self.assertContains(response, BFCACHE_SCRIPT, status_code=HTTPStatus.FORBIDDEN)

    def test_login_page_has_no_reload_script(self) -> None:
        """A visitor who is not logged in gets no script."""
        self.assertNotContains(self.client.get(LOGIN_URL), BFCACHE_SCRIPT)

    def test_login_page_after_logout_has_no_reload_script(self) -> None:
        """After Log out the login page is a logged-out page."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        response = self.client.post(LOGOUT_URL, follow=True)
        self.assertNotContains(response, BFCACHE_SCRIPT)

    def test_home_page_still_sends_no_cache_headers(self) -> None:
        """The script adds to never_cache; it does not replace it."""
        self.post_login(STUDENT_ID, GOOD_PASSWORD)
        cache_control = self.client.get(HOME_URL).headers["Cache-Control"]
        for directive in ("no-cache", "no-store", "must-revalidate", "private"):
            with self.subTest(directive=directive):
                self.assertIn(directive, cache_control)


class CsrfTests(AuthPageTestCase):
    """Log out and every form are protected against cross-site requests."""

    def setUp(self) -> None:
        """Use a client that checks CSRF tokens like a real browser would."""
        super().setUp()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(User.objects.get(username=STUDENT_ID))

    def test_logout_without_token_is_refused(self) -> None:
        """A forged log out (no CSRF token) is refused, the user stays in."""
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assert_logged_in()

    def test_navbar_logout_form_contains_token(self) -> None:
        """The rendered Log out form carries the token, and it works."""
        response = self.client.get(HOME_URL)
        self.assertContains(response, CSRF_FIELD)
        token = response.context["csrf_token"]
        response = self.client.post(LOGOUT_URL, {"csrfmiddlewaretoken": token})
        self.assertRedirects(response, LOGIN_URL)
        self.assert_logged_out()

    def test_every_post_form_in_templates_has_token(self) -> None:
        """Each <form method="post"> in every template has a csrf_token."""
        for template in TEMPLATES_DIR.glob("*.html"):
            with self.subTest(template=template.name):
                source = template.read_text(encoding="utf-8")
                self.assertEqual(
                    source.count('<form method="post"'),
                    source.count("{% csrf_token %}"),
                )


class IdleTimeoutTests(AuthPageTestCase):
    """The session ends after 15 minutes without a request (FR-03 AC 3).

    The rule is "idle time >= 15 minutes", so at exactly 15:00 the user is
    logged out (see test_idle_exactly_fifteen_minutes_logs_out).
    """

    def setUp(self) -> None:
        """Log in at START_TIME."""
        super().setUp()
        self.post_login(STUDENT_ID, GOOD_PASSWORD)

    def test_idle_fourteen_fifty_nine_stays_logged_in(self) -> None:
        """Boundary: 14:59 idle keeps the session."""
        self.move_clock(IDLE_TIMEOUT - ONE_SECOND)
        self.assert_logged_in()

    def test_idle_fifteen_oh_one_logs_out_with_message(self) -> None:
        """AC 3, boundary: 15:01 idle ends the session and shows the message."""
        self.move_clock(IDLE_TIMEOUT + ONE_SECOND)
        response = self.client.get(HOME_URL, follow=True)
        self.assertRedirects(response, LOGIN_URL)
        self.assertContains(response, MSG_SESSION_EXPIRED)
        self.assert_logged_out()

    def test_idle_exactly_fifteen_minutes_logs_out(self) -> None:
        """Boundary: at exactly 15:00 the session has expired."""
        self.move_clock(IDLE_TIMEOUT)
        self.assertRedirects(self.client.get(HOME_URL), LOGIN_URL)

    def test_each_request_restarts_the_idle_timer(self) -> None:
        """Activity counts from the last request, not from the login."""
        self.move_clock(IDLE_TIMEOUT - ONE_SECOND)
        self.assert_logged_in()
        self.move_clock(2 * IDLE_TIMEOUT - 2 * ONE_SECOND)
        self.assert_logged_in()

    def test_logged_out_visitor_is_not_affected(self) -> None:
        """A visitor who is not logged in never sees the expired message."""
        self.client.post(LOGOUT_URL)
        self.move_clock(IDLE_TIMEOUT + ONE_SECOND)
        self.assertNotContains(self.client.get(LOGIN_URL), MSG_SESSION_EXPIRED)


class RoleRequiredTests(AuthPageTestCase):
    """role_required with a tiny view that exists only in these tests."""

    def call_view(self, user: User | AnonymousUser) -> HttpResponse:
        """Call the administrator-only test view as a given user.

        Args:
            user: The user making the request.

        Returns:
            The view's response.
        """
        request = RequestFactory().get("/test-only/")
        request.user = user
        return admin_only_view(request)

    def test_allowed_role_sees_page(self) -> None:
        """An administrator may open the administrator page."""
        response = self.call_view(self.make_active_user(ADMINISTRATOR_ID))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_wrong_role_gets_403_with_message(self) -> None:
        """AC 4: another role is denied with the SRS message."""
        response = self.call_view(User.objects.get(username=STUDENT_ID))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertContains(
            response, MSG_NOT_AUTHORIZED, status_code=HTTPStatus.FORBIDDEN
        )

    def test_wrong_role_page_uses_403_template(self) -> None:
        """The 403 page comes from 403.html."""
        self.client.force_login(User.objects.get(username=STUDENT_ID))
        with self.assertTemplateUsed(TEMPLATE_FORBIDDEN):
            self.call_view(User.objects.get(username=STUDENT_ID))

    def test_not_logged_in_goes_to_login(self) -> None:
        """A visitor who is not logged in is asked to log in."""
        response = self.call_view(AnonymousUser())
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(response.headers["Location"].startswith(LOGIN_URL))

    def test_allowed_and_denied_pages_are_never_cached(self) -> None:
        """never_cache is applied by role_required to every answer."""
        users = (
            self.make_active_user(ADMINISTRATOR_ID),
            User.objects.get(username=STUDENT_ID),
            AnonymousUser(),
        )
        for user in users:
            with self.subTest(user=str(user)):
                response = self.call_view(user)
                self.assertIn("no-store", response.headers["Cache-Control"])
