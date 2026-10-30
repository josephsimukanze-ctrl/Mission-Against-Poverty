
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.utils import timezone
from .models import Event, EventRegistration


# events/views.py
from django.utils import timezone

class EventListView(ListView):
    model = Event
    template_name = "events/list.html"
    context_object_name = "events"
    paginate_by = 9

    def get_queryset(self):
        return Event.objects.filter(published=True).order_by("-starts_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        all_events = Event.objects.filter(published=True)
        ctx["upcoming_events"] = all_events.filter(starts_at__gte=now).order_by("starts_at")
        ctx["past_events"]     = all_events.filter(starts_at__lt=now).order_by("-starts_at")[:6]
        return ctx

class EventDetailView(DetailView):
    model = Event
    template_name = "events/detail.html"
    queryset = Event.objects.filter(published=True)

        # events/views.py::EventDetailView.get_context_data
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ev = self.object

        # Spots remaining
        if ev.capacity and hasattr(ev, "registration_count"):
            ctx["spots_remaining"] = max(0, ev.capacity - (ev.registration_count or 0))

        # Related upcoming events (next 3)
        from django.utils import timezone
        ctx["related_events"] = (
            Event.objects.filter(is_published=True, starts_at__gte=timezone.now())
            .exclude(pk=ev.pk)
            .order_by("starts_at")[:3]
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

# events/views.py
from django.http import HttpResponse
from django.utils import timezone

def event_ics(request, pk):
    event = Event.objects.get(pk=pk)
    dt_stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    start = event.starts_at.strftime("%Y%m%dT%H%M%S")
    end = (event.ends_at or event.starts_at + timedelta(hours=2)).strftime("%Y%m%dT%H%M%S")

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//{ORG_NAME}//Events//EN
BEGIN:VEVENT
UID:{event.pk}@map.org
DTSTAMP:{dt_stamp}
DTSTART:{start}
DTEND:{end}
SUMMARY:{event.name}
LOCATION:{event.location or ''}
DESCRIPTION:{event.description[:200] if event.description else ''}
END:VEVENT
END:VCALENDAR"""

    response = HttpResponse(ics, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{event.slug or event.pk}.ics"'
    return response