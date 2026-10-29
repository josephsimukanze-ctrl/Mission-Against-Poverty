# core/urls.py
from django.urls import path
from .views import SiteSettingsView

app_name = "core"

urlpatterns = [
    path("settings/", SiteSettingsView.as_view(), name="settings"),
]