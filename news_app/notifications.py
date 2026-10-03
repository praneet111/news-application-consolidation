"""Reusable, transaction-safe newsletter email delivery."""

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import CustomUser


def notify_newsletter_subscribers(newsletter):
    """Send a new newsletter after its approved-article selection is saved."""
    if newsletter.publisher_id:
        readers = CustomUser.objects.filter(
            subscribed_publishers=newsletter.publisher_id
        )
    else:
        readers = CustomUser.objects.filter(
            subscribed_journalists=newsletter.author_id
        )
    emails = list(
        readers.filter(role="reader", is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    subject = f"New Newsletter: {newsletter.title}".replace("\r", " ").replace(
        "\n", " "
    )
    articles = newsletter.articles.filter(approved=True)
    sections = [newsletter.description] + [
        f"{article.title}\n{article.content}" for article in articles
    ]
    body = "\n\n".join(sections)

    def deliver():
        for email in emails:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )

    if emails:
        transaction.on_commit(deliver)
