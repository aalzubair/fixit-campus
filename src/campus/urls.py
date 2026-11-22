"""URL routes for the campus app (Presentation layer)."""

from django.urls import path

from campus import views
from campus.constants import (
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_LOGOUT,
    URL_NAME_PASSWORD_RESET,
    URL_NAME_PASSWORD_RESET_NEW_OTP,
    URL_NAME_PASSWORD_RESET_VERIFY,
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
    path("login/", views.login_view, name=URL_NAME_LOGIN),
    path("logout/", views.logout_view, name=URL_NAME_LOGOUT),
    path("home/", views.home_view, name=URL_NAME_HOME),
    path("password-reset/", views.password_reset_view, name=URL_NAME_PASSWORD_RESET),
    path(
        "password-reset/verify/",
        views.password_reset_verify_view,
        name=URL_NAME_PASSWORD_RESET_VERIFY,
    ),
    path(
        "password-reset/verify/new-otp/",
        views.password_reset_new_otp_view,
        name=URL_NAME_PASSWORD_RESET_NEW_OTP,
    ),
]
