
from django.contrib import admin
from .models import Event, EventRegistration


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_at", "location", "registration_open", "published")
    list_filter = ("published", "registration_open")
    search_fields = ("name", "location")
    inlines = [EventRegistrationInline]


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "event", "attended", "created_at")
    list_filter = ("attended", "event")
    search_fields = ("full_name", "email")
