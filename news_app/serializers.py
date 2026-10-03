"""Article serialization with protected ownership and approval fields."""

from rest_framework import serializers

from .models import Article, CustomUser, Newsletter, Publisher


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "content",
            "author",
            "publisher",
            "approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def validate_publisher(self, publisher):
        user = self.context["request"].user
        if (
            publisher is not None
            and user.role == "journalist"
            and not publisher.journalists.filter(pk=user.pk).exists()
        ):
            raise serializers.ValidationError(
                "Choose a publisher you are assigned to."
            )
        return publisher

    def validate_approved(self, approved):
        if self.context["request"].user.role != "editor" and approved:
            raise serializers.ValidationError(
                "Only editors can approve articles."
            )
        return approved


class UserSerializer(serializers.ModelSerializer):
    """Safe read-only profile; role-inapplicable fields are JSON null."""

    subscribed_publishers = serializers.SerializerMethodField()
    subscribed_journalists = serializers.SerializerMethodField()
    independent_articles = serializers.SerializerMethodField()
    independent_newsletters = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "role",
            "subscribed_publishers",
            "subscribed_journalists",
            "independent_articles",
            "independent_newsletters",
        ]
        read_only_fields = fields

    def get_subscribed_publishers(self, user):
        if user.role == "reader":
            return list(
                user.subscribed_publishers.values_list("pk", flat=True)
            )
        return None

    def get_subscribed_journalists(self, user):
        if user.role == "reader":
            return list(
                user.subscribed_journalists.values_list("pk", flat=True)
            )
        return None

    def get_independent_articles(self, user):
        if user.role == "journalist":
            return list(user.independent_articles.values_list("pk", flat=True))
        return None

    def get_independent_newsletters(self, user):
        if user.role == "journalist":
            return list(
                user.independent_newsletters.values_list("pk", flat=True)
            )
        return None


class PublisherSerializer(serializers.ModelSerializer):
    """Read-only publisher directory with its editorial assignments."""

    class Meta:
        model = Publisher
        fields = ["id", "name", "editors", "journalists"]
        read_only_fields = fields


class NewsletterSerializer(serializers.ModelSerializer):
    """Newsletter input validates the same constraints as the website."""

    articles = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Article.objects.filter(approved=True),
        required=False,
    )

    class Meta:
        model = Newsletter
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "author",
            "publisher",
            "articles",
        ]
        read_only_fields = ["id", "created_at", "author"]

    def validate_publisher(self, publisher):
        user = self.context["request"].user
        if (
            publisher is not None
            and user.role == "journalist"
            and not publisher.journalists.filter(pk=user.pk).exists()
        ):
            raise serializers.ValidationError(
                "Choose a publisher you are assigned to."
            )
        return publisher

    def to_representation(self, instance):
        result = super().to_representation(instance)
        # Linked articles may have returned to draft after newsletter creation.
        result["articles"] = [
            article.pk
            for article in instance.articles.all()
            if article.approved
        ]
        return result
