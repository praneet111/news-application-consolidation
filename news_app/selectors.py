"""Queries shared by reader pages and the API."""

from django.db.models import Q

from .models import Article


def subscribed_articles(user):
    """Return approved articles matching a reader's subscriptions.

    Include articles from subscribed publishers and independent articles
    from subscribed journalists. Exclude unapproved articles and remove
    duplicate results.

    Args:
        user: The reader whose subscriptions determine the results.

    Returns:
        QuerySet: Approved articles with author and publisher details.
    """
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
