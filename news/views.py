# news/views.py
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.utils import timezone
from .models import Article, NewsCategory, SuccessStory


class ArticleListView(ListView):
    model = Article
    template_name = "news/list.html"
    context_object_name = "articles"
    paginate_by = 9

    def get_queryset(self):
        qs = Article.objects.filter(published=True).select_related("category")
        q = self.request.GET.get("q", "").strip()
        cat = self.request.GET.get("category", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
        if cat:
            qs = qs.filter(category__slug=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = NewsCategory.objects.all()
        ctx["filters"] = {"q": self.request.GET.get("q", ""), "category": self.request.GET.get("category", "")}
        return ctx


class ArticleDetailView(DetailView):
    model = Article
    template_name = "news/detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = Article.objects.filter(published=True)


class SuccessStoryListView(ListView):
    model = SuccessStory
    template_name = "news/stories_list.html"
    context_object_name = "stories"
    paginate_by = 9
    queryset = SuccessStory.objects.filter(published=True)


class SuccessStoryDetailView(DetailView):
    model = SuccessStory
    template_name = "news/story_detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = SuccessStory.objects.filter(published=True)
