# news/models.py
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from core.models import AuthoredModel, UUIDModel


class NewsCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "News categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:100]
        super().save(*args, **kwargs)


class Article(AuthoredModel, UUIDModel):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=270, unique=True, blank=True)
    category = models.ForeignKey(NewsCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="news/", blank=True, null=True)
    published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:270]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:detail", args=[self.slug])


class SuccessStory(AuthoredModel, UUIDModel):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=270, unique=True, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="stories/", blank=True, null=True)
    consent_obtained = models.BooleanField(default=False, help_text="Required before publishing identifiable beneficiary stories.")
    published = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Success stories"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:270]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:story", args=[self.slug])
