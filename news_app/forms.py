from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Article, CustomUser, Newsletter, Publisher


class RegistrationForm(UserCreationForm):
    """
    Form for registering new users with roles.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            ("reader", "Reader"),
            ("journalist", "Journalist"),
        ]

    class Meta:
        model = CustomUser
        fields = ["username", "email", "role", "password1", "password2"]


class ArticleForm(forms.ModelForm):
    """Form for creating and editing articles."""

    class Meta:
        model = Article
        fields = ["title", "content", "publisher"]

    def __init__(self, *args, **kwargs):
        """Limit publisher choices to journalist's assigned publishers."""
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and user.role == "journalist":
            self.fields["publisher"].queryset = Publisher.objects.filter(
                journalists=user
            )


class NewsletterForm(forms.ModelForm):
    """Form for creating newsletters from approved articles."""

    class Meta:
        model = Newsletter
        fields = [
            "title",
            "description",
            "publisher",
            "articles",
        ]

    def __init__(self, *args, **kwargs):
        """Limit articles to approved content and publishers to assignments."""
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.role == "journalist":
            self.fields["publisher"].queryset = Publisher.objects.filter(
                journalists=user
            )

        self.fields["articles"].queryset = Article.objects.filter(
            approved=True
        )


class PublisherForm(forms.ModelForm):
    """Form for creating and editing publishers."""

    class Meta:
        model = Publisher
        fields = ["name", "editors", "journalists"]

    def __init__(self, *args, **kwargs):
        """Filter editor and journalist selection lists by role."""
        super().__init__(*args, **kwargs)
        self.fields["editors"].queryset = CustomUser.objects.filter(
            role="editor"
        )
        self.fields["journalists"].queryset = CustomUser.objects.filter(
            role="journalist"
        )


class AdminUserChangeForm(UserChangeForm):
    """Keep relations valid when an administrator changes a role."""

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "subscribed_journalists" in self.fields:
            self.fields[
                "subscribed_journalists"
            ].queryset = CustomUser.objects.filter(role="journalist")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") != "reader":
            for name in ("subscribed_publishers", "subscribed_journalists"):
                if name in self.fields:
                    cleaned[name] = self.fields[name].queryset.none()
        return cleaned
