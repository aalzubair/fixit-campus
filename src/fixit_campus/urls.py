"""Root URL configuration for the fixit_campus project.

All feature URLs live in ``campus/urls.py``; this file only includes them.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("campus.urls")),
]
