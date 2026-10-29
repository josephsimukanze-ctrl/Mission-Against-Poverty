# contacts/views.py
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

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