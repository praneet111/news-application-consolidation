"""Shared role and ownership rules for the website and REST API."""

from functools import wraps

from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def can_manage(user, content):
    """Editors manage all content; journalists manage only their own."""
    return user.is_authenticated and (
        user.role == "editor"
        or (user.role == "journalist" and content.author_id == user.pk)
    )


def role_required(role):
    """Require a role after the view's login_required decorator."""

    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorate


class IsJournalist(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and request.user.role == "journalist"
        )


class IsReader(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "reader"


class IsEditorOrOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "editor",
            "journalist",
        )

    def has_object_permission(self, request, view, obj):
        return can_manage(request.user, obj)
