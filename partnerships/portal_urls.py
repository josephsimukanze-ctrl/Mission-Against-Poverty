
from django.urls import path
from . import views

app_name = "partner_portal"

urlpatterns = [
    path("", views.PartnerDashboardView.as_view(), name="dashboard"),
    path("applications/", views.PartnerApplicationsListView.as_view(), name="applications"),
]
