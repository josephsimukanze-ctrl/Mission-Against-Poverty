# donations/portal_urls.py
from django.urls import path
from . import views

app_name = "donor_portal"

urlpatterns = [
    path("", views.DonorDashboardView.as_view(), name="dashboard"),
    path("history/", views.DonorHistoryView.as_view(), name="history"),
    path("receipt/<str:reference>/", views.ReceiptDownloadView.as_view(), name="receipt"),
]
