
from django.urls import path
from . import views

app_name = "volunteers"

urlpatterns = [
    path("volunteer/", views.VolunteerApplyView.as_view(), name="apply"),
    path("volunteer/done/", views.VolunteerApplyDoneView.as_view(), name="apply_done"),
    path("management/volunteers/applications/bulk/", views.BulkApplicationActionView.as_view(), name="bulk_action"),
    path("assignments/bulk-respond/", views.bulk_respond_to_assignments, name="bulk_respond"),
    path("assignments/<int:pk>/respond/<str:action>/", views.respond_to_assignment, name="respond_assignment"),
]
