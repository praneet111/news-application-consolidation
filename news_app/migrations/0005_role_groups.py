"""Populate the role groups and permissions required by the assignment."""
from django.db import migrations


def assign_groups(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model("news_app", "CustomUser")
    rules = {
        "reader": ("Reader", ("view",)),
        "editor": ("Editor", ("view", "change", "delete")),
        "journalist": ("Journalist", ("view", "add", "change", "delete")),
    }
    groups = {}
    for role, (name, actions) in rules.items():
        group, _ = Group.objects.using(alias).get_or_create(name=name)
        permissions = []
        for model in ("article", "newsletter"):
            content_type, _ = ContentType.objects.using(alias).get_or_create(
                app_label="news_app", model=model
            )
            for action in actions:
                permission, _ = Permission.objects.using(alias).get_or_create(
                    content_type=content_type, codename=f"{action}_{model}",
                    defaults={"name": f"Can {action} {model}"},
                )
                permissions.append(permission)
        group.permissions.set(permissions)
        groups[role] = group
    for user in User.objects.using(alias).all().iterator():
        desired = groups.get(user.role)
        user.groups.remove(*(group for group in groups.values() if group != desired))
        if desired:
            user.groups.add(desired)
        if user.role != "reader":
            user.subscribed_publishers.clear()
            user.subscribed_journalists.clear()


class Migration(migrations.Migration):
    dependencies = [("news_app", "0004_newsletter_author")]
    # Rollback leaves groups intact: they may be used by existing accounts.
    operations = [migrations.RunPython(assign_groups, migrations.RunPython.noop)]
