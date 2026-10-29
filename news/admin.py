from django.contrib import admin
from .models import NewsCategory, Article, SuccessStory


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "published", "published_at", "created_at")
    list_filter = ("published", "category")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "body")


@admin.register(SuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "consent_obtained", "published", "created_at")
    list_filter = ("published", "consent_obtained")
    prepopulated_fields = {"slug": ("title",)}
