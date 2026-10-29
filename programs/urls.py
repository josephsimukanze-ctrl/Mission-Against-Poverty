from django.urls import path
from . import views

app_name = "programs"

urlpatterns = [
    path("", views.ProgramListView.as_view(), name="list"),
    path("<slug:slug>/", views.ProgramDetailView.as_view(), name="detail"),
]
