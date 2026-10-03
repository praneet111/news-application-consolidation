"""Queries shared by reader pages and the API."""

from django.db.models import Q

from .models import Article


def subscribed_articles(user):
    """Publisher subscriptions plus a journalist's independent articles."""
    return (
        Article.objects.filter(approved=True)
        .filter(
            Q(publisher__in=user.subscribed_publishers.all())
            | Q(
                publisher__isnull=True,
                author__in=user.subscribed_journalists.all(),
            )
        )
        .select_related("author", "publisher")
        .distinct()
    )
