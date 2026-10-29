from django.urls import path
from . import views


app_name = "reports"

urlpatterns = [
    # ---- Dashboard ----
    path("", views.ManagementDashboardView.as_view(), name="dashboard"),

    # ---- Website content ----
    path("pages/", views.PageListView.as_view(), name="pages"),
    path("pages/new/", views.PageCreateView.as_view(), name="page_create"),
    path("pages/<uuid:pk>/edit/", views.PageUpdateView.as_view(), name="page_edit"),
    path("pages/<uuid:pk>/delete/", views.PageDeleteView.as_view(), name="page_delete"),

    path("programs/", views.ProgramListView.as_view(), name="programs"),
    path("programs/new/", views.ProgramCreateView.as_view(), name="program_create"),
    path("programs/<uuid:pk>/edit/", views.ProgramUpdateView.as_view(), name="program_edit"),
    path("programs/<uuid:pk>/delete/", views.ProgramDeleteView.as_view(), name="program_delete"),

    # ---- Hero Slides ----
    path("hero-slides/", views.HeroSlideListView.as_view(), name="hero_slides"),
    path("hero-slides/new/", views.HeroSlideCreateView.as_view(), name="hero_slide_create"),
    path("hero-slides/<uuid:pk>/edit/", views.HeroSlideUpdateView.as_view(), name="hero_slide_edit"),
    path("hero-slides/<uuid:pk>/delete/", views.HeroSlideDeleteView.as_view(), name="hero_slide_delete"),

    # ... your other routes ...

    # ---- Site Settings ----
    path("settings/", views.SiteSettingsView.as_view(), name="settings"),
]
