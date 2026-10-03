"""Handle browser requests for the news application.

Provide registration, role-specific dashboards, article review,
newsletter management, publisher management, and reader subscriptions.

Views enforce role and ownership restrictions. Article approval and
deletion require POST requests with CSRF protection.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    ArticleForm,
    NewsletterForm,
    PublisherForm,
    RegistrationForm,
)
from .models import Article, CustomUser, Newsletter, Publisher
from .notifications import notify_newsletter_subscribers
from .permissions import can_manage, role_required
from .selectors import subscribed_articles


def register(request):
    """Register a new user."""

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = RegistrationForm()

    return render(request, "news_app/register.html", {"form": form})


def home(request):
    """Display approved articles on the homepage."""

    articles = Article.objects.filter(approved=True).select_related(
        "author", "publisher"
    )

    return render(request, "news_app/home.html", {"articles": articles})


@login_required
def dashboard(request):
    """Redirect logged-in users to their role dashboard."""

    if request.user.role == "reader":
        return redirect("reader_dashboard")

    if request.user.role == "journalist":
        return redirect("journalist_dashboard")

    if request.user.role == "editor":
        return redirect("editor_dashboard")

    return redirect("home")


@login_required
@role_required("reader")
def reader_dashboard(request):
    """Display approved articles for readers."""

    articles = Article.objects.filter(approved=True).select_related(
        "author", "publisher"
    )
    only_subscribed = request.GET.get("feed") == "subscribed"
    if only_subscribed:
        articles = subscribed_articles(request.user)

    return render(
        request,
        "news_app/reader_dashboard.html",
        {"articles": articles, "only_subscribed": only_subscribed},
    )


@login_required
@role_required("journalist")
def journalist_dashboard(request):
    """Display articles created by the logged-in journalist."""

    articles = Article.objects.filter(author=request.user).select_related(
        "publisher"
    )

    return render(
        request,
        "news_app/journalist_dashboard.html",
        {"articles": articles},
    )


@login_required
@role_required("editor")
def editor_dashboard(request):
    """Display all articles for editor review and management."""

    articles = Article.objects.select_related("author", "publisher").all()

    return render(
        request,
        "news_app/editor_dashboard.html",
        {"articles": articles},
    )


@login_required
def article_detail(request, article_id):
    """Display a single article if the user has permission to view it."""

    article = get_object_or_404(Article, id=article_id)

    is_public = article.approved
    is_editor = request.user.role == "editor"
    is_owner = (
        request.user.role == "journalist"
        and article.author_id == request.user.pk
    )

    if not is_public and not is_editor and not is_owner:
        raise PermissionDenied

    return render(
        request, "news_app/article_detail.html", {"article": article}
    )


@login_required
def create_article(request):
    """Allow journalists to create articles."""

    if request.user.role != "journalist":
        raise PermissionDenied

    if request.method == "POST":
        form = ArticleForm(request.POST, user=request.user)

        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            return redirect("journalist_dashboard")
    else:
        form = ArticleForm(user=request.user)

    return render(request, "news_app/article_form.html", {"form": form})


@login_required
@require_POST
def approve_article(request, article_id):
    """Allow editors to approve articles."""

    if request.user.role != "editor":
        raise PermissionDenied

    article = get_object_or_404(Article, id=article_id)
    article.approved = True
    article.updated_at = timezone.now()
    article.save()

    return redirect("editor_dashboard")


@login_required
@require_POST
def delete_article(request, article_id):
    """Allow editors and article owners to delete articles."""

    article = get_object_or_404(Article, id=article_id)

    if request.user.role == "editor":
        article.delete()
        return redirect("editor_dashboard")

    if request.user.role == "journalist" and article.author == request.user:
        article.delete()
        return redirect("journalist_dashboard")

    raise PermissionDenied


@login_required
def edit_article(request, article_id):
    """Allow editors and article owners to edit articles."""

    article = get_object_or_404(Article, id=article_id)

    is_editor = request.user.role == "editor"
    is_owner = (
        request.user.role == "journalist" and article.author == request.user
    )

    if not is_editor and not is_owner:
        raise PermissionDenied

    if request.method == "POST":
        form = ArticleForm(
            request.POST,
            instance=article,
            user=request.user,
        )

        if form.is_valid():
            updated_article = form.save(commit=False)
            updated_article.updated_at = timezone.now()
            if not is_editor:
                updated_article.approved = False
            updated_article.save()

            if is_editor:
                return redirect("editor_dashboard")

            return redirect("journalist_dashboard")
    else:
        form = ArticleForm(
            instance=article,
            user=request.user,
        )

    return render(request, "news_app/article_form.html", {"form": form})


@login_required
def newsletter_list(request):
    """Display all newsletters."""

    newsletters = Newsletter.objects.select_related(
        "author", "publisher"
    ).prefetch_related(
        Prefetch(
            "articles",
            queryset=Article.objects.filter(approved=True).select_related(
                "author", "publisher"
            ),
            to_attr="visible_articles",
        )
    )

    return render(
        request,
        "news_app/newsletter_list.html",
        {"newsletters": newsletters},
    )


@login_required
def create_newsletter(request):
    """Allow journalists to create newsletters with automatic ownership."""

    if request.user.role != "journalist":
        raise PermissionDenied

    if request.method == "POST":
        form = NewsletterForm(request.POST, user=request.user)

        if form.is_valid():
            with transaction.atomic():
                newsletter = form.save(commit=False)
                newsletter.author = request.user
                newsletter.save()
                form.save_m2m()
                notify_newsletter_subscribers(newsletter)
            return redirect("newsletter_list")
    else:
        form = NewsletterForm(user=request.user)

    return render(request, "news_app/newsletter_form.html", {"form": form})


@login_required
def edit_newsletter(request, newsletter_id):
    """Allow editors and journalist owners to manage newsletters."""

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    if not can_manage(request.user, newsletter):
        raise PermissionDenied

    if request.method == "POST":
        form = NewsletterForm(
            request.POST, instance=newsletter, user=request.user
        )

        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.save()
            form.save_m2m()
            return redirect("newsletter_list")
    else:
        form = NewsletterForm(instance=newsletter, user=request.user)

    return render(request, "news_app/newsletter_form.html", {"form": form})


@login_required
@require_POST
def delete_newsletter(request, newsletter_id):
    """Allow editors and journalist owners to manage newsletters."""

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    if not can_manage(request.user, newsletter):
        raise PermissionDenied
    newsletter.delete()

    return redirect("newsletter_list")


@login_required
def publisher_list(request):
    """Display publishers for editor management."""

    if request.user.role != "editor":
        raise PermissionDenied

    publishers = Publisher.objects.prefetch_related("editors", "journalists")

    return render(
        request,
        "news_app/publisher_list.html",
        {"publishers": publishers},
    )


@login_required
def create_publisher(request):
    """Allow editors to create publishers."""

    if request.user.role != "editor":
        raise PermissionDenied

    if request.method == "POST":
        form = PublisherForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("publisher_list")
    else:
        form = PublisherForm()

    return render(request, "news_app/publisher_form.html", {"form": form})


@login_required
def edit_publisher(request, publisher_id):
    """Allow editors to update publisher editor and journalist assignments."""

    if request.user.role != "editor":
        raise PermissionDenied

    publisher = get_object_or_404(Publisher, id=publisher_id)

    if request.method == "POST":
        form = PublisherForm(request.POST, instance=publisher)

        if form.is_valid():
            form.save()
            return redirect("publisher_list")
    else:
        form = PublisherForm(instance=publisher)

    return render(request, "news_app/publisher_form.html", {"form": form})


@login_required
@role_required("reader")
@require_http_methods(["GET", "POST"])
def subscriptions(request):
    """Allow readers to manage only their own subscriptions."""
    if request.method == "POST":
        kind = request.POST.get("kind")
        action = request.POST.get("action")
        target_id = request.POST.get("target_id", "")
        if (
            kind not in ("publisher", "journalist")
            or action not in ("subscribe", "unsubscribe")
            or not target_id.isdecimal()
        ):
            return HttpResponseBadRequest("Invalid subscription request.")
        if kind == "publisher":
            target = get_object_or_404(Publisher, pk=target_id)
            relation = request.user.subscribed_publishers
        else:
            target = get_object_or_404(
                CustomUser, pk=target_id, role="journalist"
            )
            relation = request.user.subscribed_journalists
        if action == "subscribe":
            relation.add(target)
            messages.success(request, f"Subscribed to {target}.")
        else:
            relation.remove(target)
            messages.success(request, f"Unsubscribed from {target}.")
        return redirect("subscriptions")
    return render(
        request,
        "news_app/subscriptions.html",
        {
            "publishers": Publisher.objects.order_by("name"),
            "journalists": CustomUser.objects.filter(
                role="journalist"
            ).order_by("username"),
            "publisher_ids": set(
                request.user.subscribed_publishers.values_list("pk", flat=True)
            ),
            "journalist_ids": set(
                request.user.subscribed_journalists.values_list(
                    "pk", flat=True
                )
            ),
        },
    )
