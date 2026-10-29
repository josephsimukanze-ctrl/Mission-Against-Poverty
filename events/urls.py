from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("", views.EventListView.as_view(), name="list"),
    path("<uuid:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("<uuid:pk>/register/", views.register_for_event, name="register"),
]
