
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.utils import timezone
from .models import Event, EventRegistration


class EventListView(ListView):
    model = Event
    template_name = "events/list.html"
    context_object_name = "events"
    paginate_by = 12

    def get_queryset(self):
        return Event.objects.filter(published=True)


class EventDetailView(DetailView):
    model = Event
    template_name = "events/detail.html"
    queryset = Event.objects.filter(published=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["registration_open"] = (
            self.object.registration_open and
            (self.object.starts_at is None or self.object.starts_at > timezone.now())
        )
        return ctx


def register_for_event(request, pk):
    event = get_object_or_404(Event, pk=pk, published=True)
    if not event.registration_open:
        messages.error(request, "Registration is not open for this event.")
        return redirect("events:detail", pk=event.pk)

    if request.method == "POST":
        name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        if not name or not email:
            messages.error(request, "Name and email are required.")
            return redirect("events:detail", pk=event.pk)
        if EventRegistration.objects.filter(event=event, email=email).exists():
            messages.info(request, "You are already registered for this event.")
            return redirect("events:detail", pk=event.pk)
        EventRegistration.objects.create(
            event=event, full_name=name, email=email, phone=phone,
            user=request.user if request.user.is_authenticated else None,
        )
        messages.success(request, "You are registered. A confirmation will be sent by email.")
        return redirect("events:detail", pk=event.pk)

    return redirect("events:detail", pk=event.pk)
