"""URL routes for the campus app (Presentation layer)."""

from django.urls import path

from campus import views
from campus.constants import (
    URL_NAME_COMPLAINT_DETAIL,
    URL_NAME_COMPLAINT_PHOTO,
    URL_NAME_COMPLAINT_SUBMITTED,
    URL_NAME_EXISTING_COMPLAINTS,
    URL_NAME_FOLLOW_COMPLAINT,
    URL_NAME_HOME,
    URL_NAME_LOGIN,
    URL_NAME_LOGOUT,
    URL_NAME_MY_COMPLAINTS,
    URL_NAME_PASSWORD_RESET,
    URL_NAME_PASSWORD_RESET_NEW_OTP,
    URL_NAME_PASSWORD_RESET_VERIFY,
    URL_NAME_REGISTER,
    URL_NAME_REGISTER_DONE,
    URL_NAME_REGISTER_NEW_OTP,
    URL_NAME_REGISTER_VERIFY,
    URL_NAME_REOPEN_COMPLAINT,
    URL_NAME_SIMILAR_COMPLAINTS,
    URL_NAME_SUBMIT_COMPLAINT,
    URL_NAME_UNFOLLOW_COMPLAINT,
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
    # Fixed paths first, so "new", "existing" and "mine" are never read as an ID.
    path(
        "complaints/new/",
        views.submit_complaint_view,
        name=URL_NAME_SUBMIT_COMPLAINT,
    ),
    path(
        "complaints/new/similar/",
        views.similar_complaints_view,
        name=URL_NAME_SIMILAR_COMPLAINTS,
    ),
    path(
        "complaints/existing/",
        views.existing_complaints_view,
        name=URL_NAME_EXISTING_COMPLAINTS,
    ),
    path("complaints/mine/", views.my_complaints_view, name=URL_NAME_MY_COMPLAINTS),
    path(
        "complaints/<str:complaint_id>/",
        views.complaint_detail_view,
        name=URL_NAME_COMPLAINT_DETAIL,
    ),
    path(
        "complaints/<str:complaint_id>/submitted/",
        views.complaint_submitted_view,
        name=URL_NAME_COMPLAINT_SUBMITTED,
    ),
    path(
        "complaints/<str:complaint_id>/photo/",
        views.complaint_photo_view,
        name=URL_NAME_COMPLAINT_PHOTO,
    ),
    path(
        "complaints/<str:complaint_id>/follow/",
        views.follow_complaint_view,
        name=URL_NAME_FOLLOW_COMPLAINT,
    ),
    path(
        "complaints/<str:complaint_id>/unfollow/",
        views.unfollow_complaint_view,
        name=URL_NAME_UNFOLLOW_COMPLAINT,
    ),
    path(
        "complaints/<str:complaint_id>/reopen/",
        views.reopen_complaint_view,
        name=URL_NAME_REOPEN_COMPLAINT,
    ),
]
