from django.urls import path
from django.views.generic import TemplateView
app_name = "beneficiary_portal"
urlpatterns = [path("", TemplateView.as_view(template_name="portal/placeholder.html"), name="dashboard")]
