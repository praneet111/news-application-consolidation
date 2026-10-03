"""Article API with explicit role, ownership and publication permissions."""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Article, Newsletter, Publisher
from .notifications import notify_newsletter_subscribers
from .permissions import IsEditorOrOwner, IsJournalist, IsReader
from .selectors import subscribed_articles
from .serializers import (
    ArticleSerializer,
    NewsletterSerializer,
    PublisherSerializer,
    UserSerializer,
)


class ArticleWriteMixin:
    """Share ownership and approval rules across article routes."""

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, approved=False)

    def perform_update(self, serializer):
        overrides = {"updated_at": timezone.now()}
        if self.request.user.role == "journalist":
            overrides["approved"] = False
        serializer.save(**overrides)


class ArticleListView(ArticleWriteMixin, generics.ListCreateAPIView):
    queryset = Article.objects.filter(approved=True).select_related(
        "author", "publisher"
    )
    serializer_class = ArticleSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsJournalist()]
        return [AllowAny()]


class ArticleDetailView(
    ArticleWriteMixin, generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ArticleSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsEditorOrOwner()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = Article.objects.select_related("author", "publisher")
        user = self.request.user
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return queryset
        if user.is_authenticated and user.role == "editor":
            return queryset
        if user.is_authenticated and user.role == "journalist":
            return queryset.filter(Q(approved=True) | Q(author=user))
        return queryset.filter(approved=True)


class SubscribedArticlesView(generics.ListAPIView):
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, IsReader]

    def get_queryset(self):
        return subscribed_articles(self.request.user)


class ArticleCreateView(ArticleWriteMixin, generics.CreateAPIView):
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, IsJournalist]


class ArticleUpdateView(ArticleWriteMixin, generics.UpdateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, IsEditorOrOwner]


class ArticleDeleteView(generics.DestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated, IsEditorOrOwner]


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class PublisherListView(generics.ListAPIView):
    queryset = Publisher.objects.prefetch_related("editors", "journalists")
    serializer_class = PublisherSerializer
    permission_classes = [IsAuthenticated]


class NewsletterListView(generics.ListCreateAPIView):
    queryset = Newsletter.objects.select_related(
        "author", "publisher"
    ).prefetch_related("articles")
    serializer_class = NewsletterSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsJournalist()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        with transaction.atomic():
            newsletter = serializer.save(author=self.request.user)
            notify_newsletter_subscribers(newsletter)


class NewsletterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Newsletter.objects.select_related(
        "author", "publisher"
    ).prefetch_related("articles")
    serializer_class = NewsletterSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAuthenticated(), IsEditorOrOwner()]
        return [IsAuthenticated()]
