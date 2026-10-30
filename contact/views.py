# contacts/views.py
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_POST

from .forms import ContactForm


class ContactView(View):
    template_name = "contacts/contact.html"

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "name": request.user.get_full_name() or request.user.get_username(),
                "email": request.user.email,
            }
        return render(request, self.template_name, {"form": ContactForm(initial=initial)})

    def post(self, request):
        form = ContactForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        msg = form.save(commit=False)
        if request.user.is_authenticated:
            msg.user = request.user
        msg.ip_address = request.META.get("REMOTE_ADDR")
        msg.save()

        messages.success(request, "Thanks for reaching out — we'll be in touch soon.")
        return redirect("/contact/")


@require_POST
def newsletter_subscribe(request):
    from newsletter.models import NewsletterSubscriber

    email = (request.POST.get("email") or "").strip().lower()
    name = (request.POST.get("name") or "").strip()

    if not email:
        messages.error(request, "Please enter your email address.")
        return HttpResponseRedirect(reverse("contact"))

    obj, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={"name": name, "source": "contact_page"},
    )
    if created:
        messages.success(request, "Thank you — you're subscribed!")
    else:
        messages.info(request, "You're already on the list. Thanks!")

    return HttpResponseRedirect(request.META.get("HTTP_REFERER") or reverse("contact"))