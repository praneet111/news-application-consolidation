"""Trusted administration with safe custom-user password handling."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserChangeForm
from .models import Article, CustomUser, Newsletter, Publisher


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = AdminUserChangeForm
    fieldsets = UserAdmin.fieldsets + (
        (
            "News role and subscriptions",
            {
                "fields": (
                    "role",
                    "subscribed_publishers",
                    "subscribed_journalists",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("News role", {"fields": ("role", "email")}),
    )
    list_display = UserAdmin.list_display + ("role",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        from .roles import sync_user_role

        sync_user_role(form.instance)

    filter_horizontal = UserAdmin.filter_horizontal + (
        "subscribed_publishers",
        "subscribed_journalists",
    )


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "publisher", "created_at")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = CustomUser.objects.filter(role="journalist")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Publisher)
admin.site.register(Article)
