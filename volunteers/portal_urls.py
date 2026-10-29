
from django.urls import path
from . import views

app_name = "volunteer_portal"

urlpatterns = [
    path("", views.VolunteerDashboardView.as_view(), name="dashboard"),
    path("assignments/", views.VolunteerAssignmentsView.as_view(), name="portal_assignments"),
    path("assignments/<uuid:pk>/<str:action>/", views.respond_to_assignment, name="respond_assignment"),
    path("hours/", views.VolunteerHoursView.as_view(), name="portal_hours"),
    path("certificates/", views.VolunteerCertificatesView.as_view(), name="portal_certificates"),
]
