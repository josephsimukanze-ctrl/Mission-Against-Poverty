from django.urls import path
from . import views

app_name = "beneficiaries"

urlpatterns = [
    path("request-assistance/", views.AssistanceRequestView.as_view(), name="apply"),
    path("request-assistance/done/", views.AssistanceRequestDoneView.as_view(), name="apply_done"),
]
