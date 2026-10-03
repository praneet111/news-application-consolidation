"""API URL routes for the news application."""

from django.urls import path

from .api_views import (
    ArticleCreateView,
    ArticleDeleteView,
    ArticleDetailView,
    ArticleListView,
    ArticleUpdateView,
    CurrentUserView,
    NewsletterDetailView,
    NewsletterListView,
    PublisherListView,
    SubscribedArticlesView,
)

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="api_me"),
    path("publishers/", PublisherListView.as_view(), name="api_publishers"),
    path("newsletters/", NewsletterListView.as_view(), name="api_newsletters"),
    path(
        "newsletters/<int:pk>/",
        NewsletterDetailView.as_view(),
        name="api_newsletter_detail",
    ),
    path("articles/", ArticleListView.as_view(), name="api_articles"),
    path(
        "articles/subscribed/",
        SubscribedArticlesView.as_view(),
        name="api_subscribed_articles",
    ),
    path("articles/<int:pk>/", ArticleDetailView.as_view(), name="api_detail"),
    path(
        "articles/create/",
        ArticleCreateView.as_view(),
        name="api_create_article",
    ),
    path(
        "articles/<int:pk>/update/",
        ArticleUpdateView.as_view(),
        name="api_update_article",
    ),
    path(
        "articles/<int:pk>/delete/",
        ArticleDeleteView.as_view(),
        name="api_delete_article",
    ),
]
