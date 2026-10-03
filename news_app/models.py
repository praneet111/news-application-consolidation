"""Database models for the news application."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Publisher(models.Model):
    """Represents a publisher or news organisation."""

    name = models.CharField(max_length=255)

    editors = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="publisher_editors",
    )

    journalists = models.ManyToManyField(
        "CustomUser",
        blank=True,
        related_name="publisher_journalists",
    )

    def __str__(self):
        """Return the publisher name."""
        return self.name


class CustomUser(AbstractUser):
    """Custom user model with role-based access."""

    REQUIRED_FIELDS = ["email", "role"]

    ROLE_CHOICES = (
        ("reader", "Reader"),
        ("editor", "Editor"),
        ("journalist", "Journalist"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    subscribed_publishers = models.ManyToManyField(
        Publisher,
        blank=True,
        related_name="subscribers",
    )

    subscribed_journalists = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="followers",
    )

    @property
    def independent_articles(self):
        """Journalist-only reverse relation; not applicable to other roles."""
        if self.role != "journalist":
            return None
        return self.article_set.filter(publisher__isnull=True)

    @property
    def independent_newsletters(self):
        """Journalist-only reverse relation without duplicating ownership."""
        if self.role != "journalist":
            return None
        return self.newsletters.filter(publisher__isnull=True)

    def __str__(self):
        """Return the username."""
        return self.username


class Article(models.Model):
    """Represents a news article submitted by a journalist."""

    title = models.CharField(max_length=255)
    content = models.TextField()

    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
    )

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        """Return the article title."""
        return self.title


class Newsletter(models.Model):
    """Represents a curated collection of approved articles."""

    title = models.CharField(max_length=255)
    description = models.TextField()

    # Legacy newsletters remain unassigned until their author is known.
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="newsletters",
        null=True,
        blank=True,
    )

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    articles = models.ManyToManyField(
        Article,
        blank=True,
        related_name="newsletters",
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        """Return the newsletter title."""
        return self.title
