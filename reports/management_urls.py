# reports/management_urls.py
from django.urls import path

from . import views
from core.views import SiteSettingsView
from volunteers.views import (
    VolunteerListView,
    ApplicationListView as VolunteerApplicationListView,
    ApplicationDetailView as VolunteerApplicationDetailView,
)
from partnerships.views import (
    ApplicationListView as PartnershipApplicationListView,
    ApplicationDetailView as PartnershipApplicationDetailView,
)
from newsletter.management_views import (
    SubscriberListView, SubscriberCreateView, SubscriberUpdateView, SubscriberDeleteView,
    CampaignListView, CampaignCreateView, CampaignUpdateView, CampaignDeleteView,
)
from contact.management_views import (
    ContactMessageListView,
    ContactMessageDetailView,
)

app_name = "management"

urlpatterns = [
    path("", views.ManagementDashboardView.as_view(), name="dashboard"),

    # ============================================================
    # Website
    # ============================================================
    path("pages/", views.PageListView.as_view(), name="pages"),
    path("pages/new/", views.PageCreateView.as_view(), name="page_create"),
    path("pages/<uuid:pk>/edit/", views.PageUpdateView.as_view(), name="page_edit"),
    path("pages/<uuid:pk>/delete/", views.PageDeleteView.as_view(), name="page_delete"),

    path("hero-slides/", views.HeroSlideListView.as_view(), name="hero_slides"),
    path("hero-slides/new/", views.HeroSlideCreateView.as_view(), name="hero_slide_create"),
    path("hero-slides/<uuid:pk>/edit/", views.HeroSlideUpdateView.as_view(), name="hero_slide_edit"),
    path("hero-slides/<uuid:pk>/delete/", views.HeroSlideDeleteView.as_view(), name="hero_slide_delete"),
    path("hero-slides/<uuid:pk>/photo/", views.HeroSlidePhotoUploadView.as_view(), name="hero_slide_photo"),

    path("programs/", views.ProgramListView.as_view(), name="programs"),
    path("programs/new/", views.ProgramCreateView.as_view(), name="program_create"),
    path("programs/<uuid:pk>/edit/", views.ProgramUpdateView.as_view(), name="program_edit"),
    path("programs/<uuid:pk>/delete/", views.ProgramDeleteView.as_view(), name="program_delete"),

    path("project-categories/", views.ProjectCategoryListView.as_view(), name="project_categories"),
    path("project-categories/new/", views.ProjectCategoryCreateView.as_view(), name="project_category_create"),
    path("project-categories/<uuid:pk>/edit/", views.ProjectCategoryUpdateView.as_view(), name="project_category_edit"),
    path("project-categories/<uuid:pk>/delete/", views.ProjectCategoryDeleteView.as_view(), name="project_category_delete"),

    path("projects/", views.ProjectListView.as_view(), name="projects"),
    path("projects/new/", views.ProjectCreateView.as_view(), name="project_create"),
    path("projects/<uuid:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_edit"),
    path("projects/<uuid:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),

    path("news-categories/", views.NewsCategoryListView.as_view(), name="news_categories"),
    path("news-categories/new/", views.NewsCategoryCreateView.as_view(), name="news_category_create"),
    path("news-categories/<uuid:pk>/edit/", views.NewsCategoryUpdateView.as_view(), name="news_category_edit"),
    path("news-categories/<uuid:pk>/delete/", views.NewsCategoryDeleteView.as_view(), name="news_category_delete"),

    path("news/", views.ArticleListView.as_view(), name="news"),
    path("news/new/", views.ArticleCreateView.as_view(), name="article_create"),
    path("news/<uuid:pk>/edit/", views.ArticleUpdateView.as_view(), name="article_edit"),
    path("news/<uuid:pk>/delete/", views.ArticleDeleteView.as_view(), name="article_delete"),

    path("events/", views.EventListView.as_view(), name="events"),
    path("events/new/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<uuid:pk>/edit/", views.EventUpdateView.as_view(), name="event_edit"),
    path("events/<uuid:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),

    # Leadership & Founders
    path("leadership/", views.LeadershipMemberListView.as_view(), name="leadership"),
    path("leadership/new/", views.LeadershipMemberCreateView.as_view(), name="leadership_create"),
    path("leadership/<uuid:pk>/edit/", views.LeadershipMemberUpdateView.as_view(), name="leadership_edit"),
    path("leadership/<uuid:pk>/delete/", views.LeadershipMemberDeleteView.as_view(), name="leadership_delete"),
    path("leadership/<uuid:pk>/photo/", views.LeadershipPhotoUploadView.as_view(), name="leadership_photo"),

    # ============================================================
    # People
    # ============================================================
    path("users/", views.UserListView.as_view(), name="users"),
    path("users/<uuid:pk>/", views.UserDetailView.as_view(), name="user_detail"),

    path("volunteers/", VolunteerListView.as_view(), name="volunteer_list"),
    path("volunteers/applications/", VolunteerApplicationListView.as_view(), name="volunteer_applications"),
    path("volunteers/applications/<uuid:pk>/", VolunteerApplicationDetailView.as_view(), name="volunteer_application_detail"),

    path("partnerships/", PartnershipApplicationListView.as_view(), name="partnerships"),
    path("partnerships/applications/", PartnershipApplicationListView.as_view(), name="partnership_applications"),
    path("partnerships/applications/<uuid:pk>/", PartnershipApplicationDetailView.as_view(), name="partnership_application_detail"),

    path("newsletter/", SubscriberListView.as_view(), name="newsletter"),
    path("newsletter/new/", SubscriberCreateView.as_view(), name="subscriber_create"),
    path("newsletter/<uuid:pk>/edit/", SubscriberUpdateView.as_view(), name="subscriber_edit"),
    path("newsletter/<uuid:pk>/delete/", SubscriberDeleteView.as_view(), name="subscriber_delete"),

    path("newsletter/campaigns/", CampaignListView.as_view(), name="newsletter_campaigns"),
    path("newsletter/campaigns/new/", CampaignCreateView.as_view(), name="newsletter_campaign_create"),
    path("newsletter/campaigns/<uuid:pk>/edit/", CampaignUpdateView.as_view(), name="newsletter_campaign_edit"),
    path("newsletter/campaigns/<uuid:pk>/delete/", CampaignDeleteView.as_view(), name="newsletter_campaign_delete"),

    # ============================================================
    # Finance
    # ============================================================
    path("donations/", views.DonationListView.as_view(), name="donations"),
    path("donations/new/", views.DonationCreateView.as_view(), name="donation_create"),
    path("donations/<uuid:pk>/", views.DonationDetailView.as_view(), name="donation_detail"),
    path("donations/<uuid:pk>/edit/", views.DonationUpdateView.as_view(), name="donation_edit"),
    path("donations/<uuid:pk>/delete/", views.DonationDeleteView.as_view(), name="donation_delete"),

    path("campaigns/", views.CampaignListView.as_view(), name="campaigns"),
    path("campaigns/new/", views.CampaignCreateView.as_view(), name="campaign_create"),
    path("campaigns/<uuid:pk>/edit/", views.CampaignUpdateView.as_view(), name="campaign_edit"),
    path("campaigns/<uuid:pk>/delete/", views.CampaignDeleteView.as_view(), name="campaign_delete"),

    # ============================================================
    # System
    # ============================================================
    path("reports/", views.ReportsView.as_view(), name="reports"),
    path("reports/export/donations/", views.ReportsExportCSVView.as_view(), name="reports_export_donations"),
    # Beneficiaries
    path("beneficiaries/", views.AssistanceRequestListView.as_view(), name="assistance_requests"),
    path("beneficiaries/<uuid:pk>/", views.AssistanceRequestDetailView.as_view(), name="assistance_request_detail"),

    path("audit/", views.AuditListView.as_view(), name="audit"),
    path("settings/", SiteSettingsView.as_view(), name="settings"),

    path("contacts/", ContactMessageListView.as_view(), name="contacts"),
    path("contacts/<uuid:pk>/", ContactMessageDetailView.as_view(), name="contact_detail"),
]
