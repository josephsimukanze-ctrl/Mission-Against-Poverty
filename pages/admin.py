# pages/admin.py
from django.contrib import admin
from .models import Page, LeadershipMember, MediaAsset


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "published", "updated_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "slug")


@admin.register(LeadershipMember)
class LeadershipMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "uploaded_by", "created_at")

from django.contrib import admin
from django.utils.html import format_html
from .models import HeroSlide


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display       = ("thumb", "title", "order", "is_active", "created_at")
    list_display_links = ("thumb", "title")
    list_editable      = ("order", "is_active")
    list_filter        = ("is_active",)
    readonly_fields    = ("created_at", "preview")

    @admin.display(description="Thumbnail")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:36px;width:56px;object-fit:cover;'
                'border-radius:4px;border:1px solid #e5e9f0" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:280px;border-radius:8px;'
                'border:1px solid #e5e9f0" />',
                obj.image.url,
            )
        return "Upload an image to see a preview."