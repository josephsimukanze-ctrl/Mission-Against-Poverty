# config/urls.py
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Public
    path("", include("pages.urls")),
    path("accounts/", include("accounts.urls")),
    path("programs/", include("programs.urls")),
    path("projects/", include("projects.urls")),
    path("news/", include("news.urls")),
    path("events/", include("events.urls")),
    path("", include("volunteers.urls")),  # /volunteer/, /volunteer/done/
    path("", include("partnerships.urls")),  # /partnerships/, /partnerships/done/
    path("", include("donations.urls")),  # donate/, campaigns/, thank-you/, confirm/

    # Portal shells (per stage)
    path("portal/donor/", include("donations.portal_urls")),
    path("portal/volunteer/", include("volunteers.portal_urls")),
    path("portal/partner/", include("partnerships.portal_urls")),
    path("portal/beneficiary/", include("beneficiaries.portal_urls")),

    # Management shell
    path("management/", include("reports.management_urls")),
    path("management/", include("core.urls")),
    path("newsletter/", include("newsletter.urls")),
    path("", include("beneficiaries.urls")),
    path("contact/", include("contact.urls")),   # not "contacts.urls"
    
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
