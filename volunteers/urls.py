
from django.urls import path
from . import views

app_name = "volunteers"

urlpatterns = [
    path("volunteer/", views.VolunteerApplyView.as_view(), name="apply"),
    path("volunteer/done/", views.VolunteerApplyDoneView.as_view(), name="apply_done"),
]
