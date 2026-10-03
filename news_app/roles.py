"""Django groups mirror the application's role and model permissions."""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLE_GROUPS = {
    "reader": "Reader",
    "editor": "Editor",
    "journalist": "Journalist",
}
ROLE_ACTIONS = {
    "reader": ("view",),
    "editor": ("view", "change", "delete"),
    "journalist": ("view", "add", "change", "delete"),
}


def sync_user_role(user, using="default"):
    """Replace managed role groups; preserve unrelated memberships."""
    desired_name = ROLE_GROUPS.get(user.role)
    managed = Group.objects.using(using).filter(name__in=ROLE_GROUPS.values())
    user.groups.remove(*managed.exclude(name=desired_name))
    if desired_name:
        group, _ = Group.objects.using(using).get_or_create(name=desired_name)
        user.groups.add(group)
    if user.role != "reader":
        # Many-to-many relations represent 'None' as no join-table rows.
        user.subscribed_publishers.clear()
        user.subscribed_journalists.clear()
    for cache in ("_perm_cache", "_group_perm_cache", "_user_perm_cache"):
        user.__dict__.pop(cache, None)


def configure_role_groups(sender, using="default", **kwargs):
    """Create permissions after migration and backfill existing accounts."""
    from .models import CustomUser

    for role, group_name in ROLE_GROUPS.items():
        group, _ = Group.objects.using(using).get_or_create(name=group_name)
        permissions = []
        for model in ("article", "newsletter"):
            content_type, _ = ContentType.objects.using(using).get_or_create(
                app_label="news_app", model=model
            )
            for action in ROLE_ACTIONS[role]:
                permission, _ = Permission.objects.using(using).get_or_create(
                    content_type=content_type,
                    codename=f"{action}_{model}",
                    defaults={"name": f"Can {action} {model}"},
                )
                permissions.append(permission)
        group.permissions.set(permissions)
    for user in CustomUser.objects.using(using).all().iterator():
        sync_user_role(user, using)
