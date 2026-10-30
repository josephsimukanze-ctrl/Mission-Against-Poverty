# contact/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.ContactView.as_view(), name="contact"),
    path("newsletter/", views.newsletter_subscribe, name="newsletter_subscribe"),
]