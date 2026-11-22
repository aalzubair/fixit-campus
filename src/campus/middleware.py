"""Ends the session of a user who has been inactive too long (FR-03, NFR-07).

Part of the Presentation layer: it works only with the request and the
session, so it imports nothing from the project except ``constants``.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone

from campus.constants import (
    MSG_SESSION_EXPIRED,
    SESSION_IDLE_TIMEOUT_MINUTES,
    SESSION_LAST_ACTIVITY,
    URL_NAME_LOGIN,
)


class IdleTimeoutMiddleware:  # pylint: disable=too-few-public-methods
    """Log out a user whose last request was too long ago.

    The time of each request by a logged-in user is kept in the session.
    It is saved AFTER the view runs, so the login request itself is
    stamped. Must come after the session, authentication and message
    middleware in ``settings.MIDDLEWARE``.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Remember the next step in the middleware chain.

        Args:
            get_response: Calls the next middleware or the view.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """End an idle session, or handle the request and stamp the time.

        Args:
            request: The HTTP request.

        Returns:
            A redirect to the login page if the session expired, otherwise
            the normal response.
        """
        now = timezone.now()
        if request.user.is_authenticated and _is_idle_too_long(request, now):
            logout(request)
            messages.info(request, MSG_SESSION_EXPIRED)
            return redirect(URL_NAME_LOGIN)
        response = self.get_response(request)
        if request.user.is_authenticated:
            # The session stores JSON, so the time is kept as text.
            request.session[SESSION_LAST_ACTIVITY] = now.isoformat()
        return response


def _is_idle_too_long(request: HttpRequest, now: datetime) -> bool:
    """Tell whether the last request was at least the timeout ago.

    A session without a stamp (for example one started before this
    middleware existed) counts as active, and is stamped by this request.

    Args:
        request: The HTTP request of a logged-in user.
        now: The current time.

    Returns:
        True if the user has been inactive for the whole timeout or longer.
    """
    last_activity = request.session.get(SESSION_LAST_ACTIVITY)
    if last_activity is None:
        return False
    idle_time = now - datetime.fromisoformat(last_activity)
    return idle_time >= timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES)
