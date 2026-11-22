"""URL routes for the campus app (Presentation layer)."""

from django.urls import path

from campus import views
from campus.constants import (
    URL_NAME_REGISTER,
    URL_NAME_REGISTER_DONE,
    URL_NAME_REGISTER_NEW_OTP,
    URL_NAME_REGISTER_VERIFY,
)

urlpatterns = [
    path("register/", views.register_view, name=URL_NAME_REGISTER),
    path("register/verify/", views.register_verify_view, name=URL_NAME_REGISTER_VERIFY),
    path(
        "register/verify/new-otp/",
        views.register_new_otp_view,
        name=URL_NAME_REGISTER_NEW_OTP,
    ),
    path("register/done/", views.register_done_view, name=URL_NAME_REGISTER_DONE),
]
