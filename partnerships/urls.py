
from django.urls import path
from . import views

app_name = "partnerships"

urlpatterns = [
    path("partnerships/", views.PartnershipApplyView.as_view(), name="apply"),
    path("partnerships/done/", views.PartnershipApplyDoneView.as_view(), name="apply_done"),
]
