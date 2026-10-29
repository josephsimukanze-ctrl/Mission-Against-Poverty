# newsletter/urls.py
from django.urls import path
from .views import SubscribeView

app_name = "newsletter"

urlpatterns = [
    path("subscribe/", SubscribeView.as_view(), name="subscribe"),
]