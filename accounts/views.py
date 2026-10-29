# accounts/views.py
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView

from audit.services import log_action
from .forms import RegisterForm, LoginForm, ProfileForm, UserProfileForm
from .models import Role, UserProfile


ROLE_HOME = {
    Role.DONOR: "/portal/donor/",
    Role.VOLUNTEER: "/portal/volunteer/",
    Role.PARTNER: "/portal/partner/",
    Role.BENEFICIARY: "/portal/beneficiary/",
    Role.CASE_OFFICER: "/management/",
    Role.VOLUNTEER_COORDINATOR: "/management/",
    Role.FUNDRAISING_OFFICER: "/management/",
    Role.FINANCE_OFFICER: "/management/",
    Role.PROJECT_MANAGER: "/management/",
    Role.COMMUNICATIONS_OFFICER: "/management/",
    Role.ADMINISTRATOR: "/management/",
}


def home_redirect_for(user):
    if not user.is_authenticated:
        return "/"
    if user.is_superuser:
        return "/management/"
    return ROLE_HOME.get(user.role, "/")


def _site_context():
    """
    Load SiteConfig for template context.

    Used explicitly by the auth views so login.html / register.html can
    access site.logo_light, site.about_hero_image, etc., even if the
    context processor is misconfigured or failing.
    """
    try:
        from settings_app.models import SiteConfig
        return {"site": SiteConfig.load()}
    except Exception:
        return {"site": None}


class RegisterView(CreateView):
    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("accounts:register_done")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_site_context())
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request, action="user.register", target=self.object)
        messages.success(self.request, "Account created. Please sign in.")
        return response


class RegisterDoneView(TemplateView):
    template_name = "accounts/register_done.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_site_context())
        return ctx


class MapLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_site_context())
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request, action="user.login", target=self.request.user)
        return redirect(home_redirect_for(self.request.user))

    def get_success_url(self):
        return home_redirect_for(self.request.user)


class MapLogoutView(LogoutView):
    next_page = "/"


class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        ctx["userprofile_form"] = UserProfileForm(instance=profile)
        ctx["portal_root"] = "/accounts/profile/"
        ctx.update(_site_context())
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        profile, _ = UserProfile.objects.get_or_create(user=self.object)
        form = ProfileForm(request.POST, instance=self.object)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid() and profile_form.is_valid():
            form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        return self.render_to_response(
            self.get_context_data(form=form, userprofile_form=profile_form)
        )