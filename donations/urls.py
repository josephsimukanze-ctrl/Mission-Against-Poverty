# donations/urls.py
from django.urls import path
from . import views

app_name = "donations"

urlpatterns = [
    path("donate/", views.DonateView.as_view(), name="donate"),
    path("donate/bank/<str:reference>/", views.BankInstructionsView.as_view(), name="bank_instructions"),
    path("donate/proof/<str:reference>/", views.SubmitProofView.as_view(), name="submit_proof"),
    path("donate/thank-you/<str:reference>/", views.ThankYouView.as_view(), name="thank_you"),
    path("donate/confirm/", views.ConfirmMockView.as_view(), name="confirm"),
    path("campaigns/", views.CampaignListView.as_view(), name="campaigns"),
    path("campaigns/<slug:slug>/", views.CampaignDetailView.as_view(), name="campaign_detail"),
]
