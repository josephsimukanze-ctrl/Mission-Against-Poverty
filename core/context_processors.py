# core/context_processors.py
"""
Template context processors for the whole site.

Registered in settings.TEMPLATES[0]["OPTIONS"]["context_processors"].

Only `site_settings` should be registered. `organization` is a legacy alias
and must NOT be added to the context_processors list — running two context
processors that both write `site` causes one to silently override the other.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def site_settings(request):
    """
    Inject the site configuration singleton into every template as `site`.

    Reads from `settings_app.SiteConfig` — the model the Site Settings page
    writes to. If it fails, logs the exception and falls back to None so
    public pages (login, error) still render.

    Templates should guard against `site` being None:
        {% if site and site.logo_light %}
    """
    from settings_app.models import SiteConfig

    try:
        site = SiteConfig.load()
    except Exception as exc:
        logger.exception("SiteConfig.load() failed in site_settings: %s", exc)
        site = None

    return {
        "site": site,
        "ORG_NAME": (
            (getattr(site, "site_name", None) if site else None)
            or getattr(settings, "ORG_NAME", "Organization")
        ),
        "ORG_CURRENCY": (
            (getattr(site, "currency", None) if site else None)
            or getattr(settings, "ORG_CURRENCY", "ZMW")
        ),
    }


def organization(request):
    """
    Legacy alias. Do NOT register this in settings — `site_settings`
    already provides everything it returns. Kept only so any stray
    import doesn't break.
    """
    return site_settings(request)