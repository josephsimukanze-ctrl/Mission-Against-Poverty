# programs/views.py
from django.views.generic import ListView, DetailView
from .models import Program


class ProgramListView(ListView):
    model = Program
    template_name = "programs/list.html"
    context_object_name = "programs"
    paginate_by = 12
    queryset = Program.objects.filter(published=True, archived=False)


class ProgramDetailView(DetailView):
    model = Program
    template_name = "programs/detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = Program.objects.filter(published=True, archived=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = self.object.project_set.filter(published=True)
        return ctx