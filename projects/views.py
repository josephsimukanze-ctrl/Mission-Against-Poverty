# projects/views.py
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Project, ProjectCategory


class ProjectListView(ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 12

    def get_queryset(self):
        qs = Project.objects.filter(published=True).select_related("program", "category")
        q = self.request.GET.get("q", "").strip()
        cat = self.request.GET.get("category", "").strip()
        status = self.request.GET.get("status", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(summary__icontains=q))
        if cat:
            qs = qs.filter(category__slug=cat)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ProjectCategory.objects.all()
        ctx["statuses"] = Project.Status.choices
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "category": self.request.GET.get("category", ""),
            "status": self.request.GET.get("status", ""),
        }
        return ctx


class ProjectDetailView(DetailView):
    model = Project
    template_name = "projects/detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = Project.objects.select_related("program", "manager").filter(published=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        milestones = self.object.milestones.all()
        ctx["milestones"] = milestones
        ctx["milestones_total"] = milestones.count()
        ctx["milestones_completed"] = milestones.filter(completed=True).count()
        return ctx