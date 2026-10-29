from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path("", views.ArticleListView.as_view(), name="list"),
    path("stories/", views.SuccessStoryListView.as_view(), name="stories"),
    path("stories/<slug:slug>/", views.SuccessStoryDetailView.as_view(), name="story"),
    path("<slug:slug>/", views.ArticleDetailView.as_view(), name="detail"),
]
