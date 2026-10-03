"""URL routes for the news application frontend."""

from django.urls import path

from .views import (
    approve_article,
    article_detail,
    create_article,
    create_newsletter,
    create_publisher,
    dashboard,
    delete_article,
    delete_newsletter,
    edit_article,
    edit_newsletter,
    edit_publisher,
    editor_dashboard,
    home,
    journalist_dashboard,
    newsletter_list,
    publisher_list,
    reader_dashboard,
    register,
    subscriptions,
)

urlpatterns = [
    path("subscriptions/", subscriptions, name="subscriptions"),
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("reader/", reader_dashboard, name="reader_dashboard"),
    path("journalist/", journalist_dashboard, name="journalist_dashboard"),
    path("editor/", editor_dashboard, name="editor_dashboard"),
    path("register/", register, name="register"),
    path("articles/create/", create_article, name="create_article"),
    path(
        "articles/<int:article_id>/",
        article_detail,
        name="article_detail",
    ),
    path(
        "articles/<int:article_id>/approve/",
        approve_article,
        name="approve_article",
    ),
    path(
        "articles/<int:article_id>/edit/",
        edit_article,
        name="edit_article",
    ),
    path(
        "articles/<int:article_id>/delete/",
        delete_article,
        name="delete_article",
    ),
    path("newsletters/", newsletter_list, name="newsletter_list"),
    path("newsletters/create/", create_newsletter, name="create_newsletter"),
    path(
        "newsletters/<int:newsletter_id>/edit/",
        edit_newsletter,
        name="edit_newsletter",
    ),
    path(
        "newsletters/<int:newsletter_id>/delete/",
        delete_newsletter,
        name="delete_newsletter",
    ),
    path("publishers/", publisher_list, name="publisher_list"),
    path("publishers/create/", create_publisher, name="create_publisher"),
    path(
        "publishers/<int:publisher_id>/edit/",
        edit_publisher,
        name="edit_publisher",
    ),
]
