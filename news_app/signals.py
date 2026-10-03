"""Email subscribers on approval transitions without external API calls."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from .models import Article, CustomUser


@receiver(pre_save, sender=Article)
def remember_approval(sender, instance, raw=False, **kwargs):
    if raw:
        return
    instance._previously_approved = bool(
        instance.pk
        and sender.objects.filter(pk=instance.pk, approved=True).exists()
    )


@receiver(post_save, sender=Article)
def notify_subscribers_on_approval(
    sender, instance, raw=False, update_fields=None, **kwargs
):
    """Send one email per reader after a successful approval transaction."""
    if (
        raw
        or not instance.approved
        or getattr(instance, "_previously_approved", False)
    ):
        return
    if update_fields is not None and "approved" not in update_fields:
        return
    if instance.publisher_id:
        subscribers = CustomUser.objects.filter(
            subscribed_publishers=instance.publisher_id
        )
    else:
        subscribers = CustomUser.objects.filter(
            subscribed_journalists=instance.author_id
        )
    emails = list(
        subscribers.filter(role="reader", is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    subject = f"New Approved Article: {instance.title}".replace(
        "\n", " "
    ).replace("\r", " ")
    content = instance.content

    def deliver():
        # Separate messages keep subscriber addresses private.
        for email in emails:
            send_mail(
                subject,
                content,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )

    if emails:
        transaction.on_commit(deliver)


@receiver(post_save, sender=CustomUser)
def sync_role_on_save(sender, instance, raw=False, using="default", **kwargs):
    """Automatically assign the role group whenever an account is saved."""
    if not raw:
        from .roles import sync_user_role

        sync_user_role(instance, using)


@receiver(m2m_changed, sender=CustomUser.subscribed_publishers.through)
@receiver(m2m_changed, sender=CustomUser.subscribed_journalists.through)
def validate_subscriptions(
    sender, instance, action, reverse, pk_set, using, **kwargs
):
    """Keep reader-only fields empty for journalists and editors."""
    if action != "pre_add" or not pk_set:
        return
    users = CustomUser.objects.using(using)
    if reverse:
        if users.filter(pk__in=pk_set).exclude(role="reader").exists():
            raise ValidationError("Only readers can subscribe.")
    elif instance.role != "reader":
        raise ValidationError("Only readers can subscribe.")
    if sender == CustomUser.subscribed_journalists.through:
        invalid_target = (
            instance.role != "journalist"
            if reverse
            else users.filter(pk__in=pk_set)
            .exclude(role="journalist")
            .exists()
        )
        if invalid_target:
            raise ValidationError("Subscriptions must target a journalist.")
