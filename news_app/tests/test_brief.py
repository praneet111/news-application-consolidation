"""Regression coverage for requirements revealed by the full assignment PDF."""

from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from news_app.models import Article, CustomUser, Newsletter, Publisher
from news_app.serializers import UserSerializer


class BriefRequirementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reader = CustomUser.objects.create_user(
            "brief-reader", role="reader", email="reader@example.com"
        )
        cls.owner = CustomUser.objects.create_user(
            "brief-owner", role="journalist"
        )
        cls.other = CustomUser.objects.create_user(
            "brief-other", role="journalist"
        )
        cls.editor = CustomUser.objects.create_user(
            "brief-editor", role="editor"
        )
        cls.publisher = Publisher.objects.create(name="Brief Publisher")
        cls.publisher.journalists.add(cls.owner)
        cls.publisher.editors.add(cls.editor)
        cls.article = Article.objects.create(
            title="Approved",
            content="Article body",
            author=cls.owner,
            approved=True,
        )
        cls.draft = Article.objects.create(
            title="Draft", content="Hidden body", author=cls.owner
        )
        cls.newsletter = Newsletter.objects.create(
            title="Weekly", description="Newsletter body", author=cls.owner
        )
        cls.newsletter.articles.add(cls.article)

    def api(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def test_role_groups_have_precise_article_and_newsletter_permissions(self):
        expected = {
            "reader": {"view"},
            "editor": {"view", "change", "delete"},
            "journalist": {"view", "add", "change", "delete"},
        }
        for user in (self.reader, self.owner, self.editor):
            self.assertEqual(
                list(user.groups.values_list("name", flat=True)),
                [user.role.title()],
            )
            for model in ("article", "newsletter"):
                for action in ("view", "add", "change", "delete"):
                    with self.subTest(
                        role=user.role, permission=f"{action}_{model}"
                    ):
                        self.assertEqual(
                            user.has_perm(f"news_app.{action}_{model}"),
                            action in expected[user.role],
                        )

    def test_role_change_replaces_managed_group_and_clears_subscriptions(self):
        custom = Group.objects.create(name="Unrelated group")
        self.reader.groups.add(custom)
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.subscribed_journalists.add(self.owner)
        self.reader.role = "journalist"
        self.reader.save()
        self.assertCountEqual(
            self.reader.groups.values_list("name", flat=True),
            ["Journalist", "Unrelated group"],
        )
        self.assertFalse(self.reader.subscribed_publishers.exists())
        self.assertFalse(self.reader.subscribed_journalists.exists())
        self.assertTrue(self.reader.has_perm("news_app.add_article"))
        self.reader.role = "editor"
        self.reader.save()
        self.assertFalse(self.reader.has_perm("news_app.add_newsletter"))

    def test_nonreaders_cannot_add_subscription_relations(self):
        for user in (self.owner, self.editor):
            with self.assertRaises(ValidationError), transaction.atomic():
                user.subscribed_publishers.add(self.publisher)
            with self.assertRaises(ValidationError), transaction.atomic():
                user.subscribed_journalists.add(self.other)
            with self.assertRaises(ValidationError), transaction.atomic():
                self.publisher.subscribers.add(user)
            self.assertEqual(user.subscribed_publishers.count(), 0)
        with self.assertRaises(ValidationError), transaction.atomic():
            self.reader.subscribed_journalists.add(self.editor)

    def test_role_inapplicable_serializer_fields_are_null(self):
        self.reader.subscribed_publishers.add(self.publisher)
        reader = UserSerializer(self.reader).data
        self.assertEqual(reader["subscribed_publishers"], [self.publisher.pk])
        self.assertIsNone(reader["independent_articles"])
        self.assertIsNone(reader["independent_newsletters"])
        journalist = UserSerializer(self.owner).data
        self.assertIsNone(journalist["subscribed_publishers"])
        self.assertIsNone(journalist["subscribed_journalists"])
        self.assertCountEqual(
            journalist["independent_articles"],
            [self.article.pk, self.draft.pk],
        )
        self.assertEqual(
            journalist["independent_newsletters"], [self.newsletter.pk]
        )
        for field in (
            "independent_articles",
            "independent_newsletters",
            "subscribed_publishers",
            "subscribed_journalists",
        ):
            self.assertIsNone(UserSerializer(self.editor).data[field])

    def test_independent_reverse_relations_exclude_publisher_content(self):
        Article.objects.create(
            title="Publisher article",
            content="Text",
            author=self.owner,
            publisher=self.publisher,
        )
        Newsletter.objects.create(
            title="Publisher newsletter",
            description="Text",
            author=self.owner,
            publisher=self.publisher,
        )
        self.assertEqual(self.owner.independent_articles.count(), 2)
        self.assertEqual(self.owner.independent_newsletters.count(), 1)
        self.assertIsNone(self.reader.independent_articles)
        self.assertIsNone(self.reader.independent_newsletters)

    def test_canonical_article_post_assigns_owner(self):
        response = self.api(self.owner).post(
            "/api/articles/",
            {"title": "New", "content": "Body", "author": self.other.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"], self.owner.pk)
        self.assertFalse(response.data["approved"])
        for user, status in (
            (None, 401),
            (self.reader, 403),
            (self.editor, 403),
        ):
            self.assertEqual(
                self.api(user)
                .post("/api/articles/", {"title": "Denied", "content": "No"})
                .status_code,
                status,
            )

    def test_canonical_put_delete_enforce_roles_and_ownership(self):
        url = f"/api/articles/{self.draft.pk}/"
        for user, status in (
            (None, 401),
            (self.reader, 403),
            (self.other, 403),
        ):
            api = self.api(user)
            self.assertEqual(
                api.put(url, {"title": "Denied", "content": "No"}).status_code,
                status,
            )
            self.assertEqual(api.delete(url).status_code, status)
        api = self.api(self.owner)
        self.assertEqual(
            api.put(
                url,
                {
                    "title": "Updated",
                    "content": "Text",
                    "author": self.other.pk,
                },
            ).status_code,
            200,
        )
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.author, self.owner)
        self.assertFalse(self.draft.approved)
        self.assertEqual(api.delete(url).status_code, 204)

    def test_canonical_editor_can_approve_and_delete(self):
        api = self.api(self.editor)
        url = f"/api/articles/{self.draft.pk}/"
        self.assertEqual(
            api.put(
                url,
                {"title": "Reviewed", "content": "Edited", "approved": True},
            ).status_code,
            200,
        )
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.approved)
        self.assertEqual(api.delete(url).status_code, 204)

    def test_canonical_author_cannot_approve_and_edit_requires_review(self):
        api = self.api(self.owner)
        url = f"/api/articles/{self.article.pk}/"
        self.assertEqual(api.patch(url, {"approved": True}).status_code, 400)
        self.assertEqual(
            api.patch(url, {"content": "New draft"}).status_code, 200
        )
        self.article.refresh_from_db()
        self.assertFalse(self.article.approved)
        self.assertEqual(self.api(self.reader).get(url).status_code, 404)

    def test_profile_endpoint_is_private_and_read_only(self):
        self.assertEqual(self.api().get(reverse("api_me")).status_code, 401)
        api = self.api(self.reader)
        response = api.get(reverse("api_me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.reader.pk)
        for secret in (
            "password",
            "email",
            "is_staff",
            "is_superuser",
            "user_permissions",
        ):
            self.assertNotIn(secret, response.data)
        self.assertEqual(
            api.patch(reverse("api_me"), {"role": "editor"}).status_code, 405
        )

    def test_publisher_serializer_is_used_in_read_only_directory(self):
        self.assertEqual(
            self.api().get(reverse("api_publishers")).status_code, 401
        )
        api = self.api(self.reader)
        response = api.get(reverse("api_publishers"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["journalists"], [self.owner.pk])
        self.assertEqual(response.data[0]["editors"], [self.editor.pk])
        self.assertEqual(
            api.post(reverse("api_publishers"), {"name": "No"}).status_code,
            405,
        )

    def test_newsletter_api_creation_requires_journalist(self):
        url = reverse("api_newsletters")
        for user, status in (
            (None, 401),
            (self.reader, 403),
            (self.editor, 403),
        ):
            self.assertEqual(
                self.api(user)
                .post(url, {"title": "No", "description": "No"})
                .status_code,
                status,
            )
        response = self.api(self.owner).post(
            url,
            {
                "title": "Created",
                "description": "Text",
                "author": self.other.pk,
                "articles": [self.article.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"], self.owner.pk)
        self.assertEqual(response.data["articles"], [self.article.pk])

    def test_newsletter_api_validation_rejects_drafts_and_foreign_publishers(
        self,
    ):
        api = self.api(self.other)
        for data in (
            {"articles": [self.draft.pk]},
            {"publisher": self.publisher.pk},
        ):
            response = api.post(
                reverse("api_newsletters"),
                {"title": "Invalid", "description": "No", **data},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Newsletter.objects.filter(title="Invalid").exists())

    def test_newsletter_api_denies_other_authors_and_readers(self):
        url = reverse("api_newsletter_detail", args=[self.newsletter.pk])
        for user in (self.reader, self.other):
            api = self.api(user)
            self.assertEqual(api.get(url).status_code, 200)
            self.assertEqual(api.patch(url, {"title": "Bad"}).status_code, 403)
            self.assertEqual(api.delete(url).status_code, 403)
        self.assertEqual(self.api().get(url).status_code, 401)

    def test_newsletter_api_owner_and_editor_can_update_and_delete(self):
        for user in (self.owner, self.editor):
            newsletter = Newsletter.objects.create(
                title="Manage", description="Text", author=self.owner
            )
            url = reverse("api_newsletter_detail", args=[newsletter.pk])
            api = self.api(user)
            self.assertEqual(
                api.put(
                    url,
                    {
                        "title": "Updated",
                        "description": "Text",
                        "author": self.other.pk,
                    },
                ).status_code,
                200,
            )
            newsletter.refresh_from_db()
            self.assertEqual(newsletter.author, self.owner)
            self.assertEqual(api.delete(url).status_code, 204)

    def test_newsletter_api_does_not_reveal_links_to_drafts(self):
        self.newsletter.articles.add(self.draft)
        api = self.api(self.reader)
        detail = api.get(
            reverse("api_newsletter_detail", args=[self.newsletter.pk])
        )
        self.assertEqual(detail.data["articles"], [self.article.pk])
        self.assertEqual(
            api.get(reverse("api_newsletters")).data[0]["articles"],
            [self.article.pk],
        )

    @patch("news_app.notifications.send_mail")
    def test_new_newsletter_email_includes_articles_after_commit(
        self, send_mail
    ):
        self.reader.subscribed_journalists.add(self.owner)
        self.client.force_login(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("create_newsletter"),
                {
                    "title": "Email edition",
                    "description": "Intro",
                    "articles": [self.article.pk],
                },
            )
            self.assertEqual(response.status_code, 302)
            send_mail.assert_not_called()
        send_mail.assert_called_once()
        args = send_mail.call_args.args
        self.assertIn("Article body", args[1])
        self.assertEqual(args[3], [self.reader.email])

    @patch("news_app.notifications.send_mail")
    def test_newsletter_api_email_goes_to_publisher_subscribers(
        self, send_mail
    ):
        self.reader.subscribed_publishers.add(self.publisher)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api(self.owner).post(
                reverse("api_newsletters"),
                {
                    "title": "Publisher edition",
                    "description": "News",
                    "publisher": self.publisher.pk,
                    "articles": [self.article.pk],
                },
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.args[3], [self.reader.email])
        with self.captureOnCommitCallbacks(execute=True):
            self.api(self.editor).patch(
                reverse("api_newsletter_detail", args=[response.data["id"]]),
                {"title": "Correction"},
            )
        send_mail.assert_called_once()

    @patch("news_app.notifications.send_mail")
    def test_invalid_newsletter_does_not_send_email(self, send_mail):
        self.reader.subscribed_journalists.add(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api(self.owner).post(
                reverse("api_newsletters"),
                {
                    "title": "Invalid",
                    "description": "No",
                    "articles": [self.draft.pk],
                },
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        send_mail.assert_not_called()

    def test_admin_role_change_does_not_restore_reader_subscriptions(self):
        from news_app.forms import AdminUserChangeForm

        class RoleEditForm(AdminUserChangeForm):
            class Meta(AdminUserChangeForm.Meta):
                fields = [
                    "username",
                    "role",
                    "subscribed_publishers",
                    "subscribed_journalists",
                ]

        self.reader.subscribed_publishers.add(self.publisher)
        form = RoleEditForm(
            instance=self.reader,
            data={
                "username": self.reader.username,
                "role": "journalist",
                "subscribed_publishers": [self.publisher.pk],
                "subscribed_journalists": [self.owner.pk],
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertFalse(updated.subscribed_publishers.exists())
        self.assertFalse(updated.subscribed_journalists.exists())
        self.assertEqual(
            list(updated.groups.values_list("name", flat=True)), ["Journalist"]
        )
