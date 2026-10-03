"""Regression tests for roles, ownership, approval and reader subscriptions."""

from django.core import mail
from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from news_app.models import Article, CustomUser, Newsletter, Publisher


class RoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reader = CustomUser.objects.create_user(
            "reader",
            password="Test-pass-42",
            role="reader",
            email="reader@example.com",
        )
        cls.owner = CustomUser.objects.create_user(
            "owner", password="Test-pass-42", role="journalist"
        )
        cls.other = CustomUser.objects.create_user(
            "other", password="Test-pass-42", role="journalist"
        )
        cls.editor = CustomUser.objects.create_user(
            "editor", password="Test-pass-42", role="editor"
        )
        cls.publisher = Publisher.objects.create(name="Daily News")
        cls.publisher.journalists.add(cls.owner)
        cls.unassigned = Publisher.objects.create(name="Other Publisher")
        cls.article = Article.objects.create(
            title="Public article",
            content="Public content",
            author=cls.owner,
            publisher=cls.publisher,
            approved=True,
        )
        cls.pending = Article.objects.create(
            title="Private draft", content="Secret content", author=cls.owner
        )
        cls.independent = Article.objects.create(
            title="Independent news",
            content="Independent content",
            author=cls.owner,
            approved=True,
        )
        cls.newsletter = Newsletter.objects.create(
            title="Weekly", description="Our news", author=cls.owner
        )
        cls.newsletter.articles.add(cls.article)

    def api(self, user=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client

    def login(self, user):
        self.client.force_login(user)

    def test_anonymous_api_writes_require_authentication(self):
        api = self.api()
        self.assertEqual(
            api.post(reverse("api_create_article"), {}).status_code, 401
        )
        self.assertEqual(
            api.patch(
                reverse("api_update_article", args=[self.article.pk]), {}
            ).status_code,
            401,
        )
        self.assertEqual(
            api.delete(
                reverse("api_delete_article", args=[self.article.pk])
            ).status_code,
            401,
        )

    def test_reader_cannot_write_article_api(self):
        api = self.api(self.reader)
        self.assertEqual(
            api.post(
                reverse("api_create_article"),
                {"title": "Attack", "content": "No"},
            ).status_code,
            403,
        )
        self.assertEqual(
            api.patch(
                reverse("api_update_article", args=[self.article.pk]),
                {"title": "Attack"},
            ).status_code,
            403,
        )
        self.assertEqual(
            api.put(
                reverse("api_update_article", args=[self.article.pk]),
                {"title": "Attack", "content": "No"},
            ).status_code,
            403,
        )
        self.assertEqual(
            api.delete(
                reverse("api_delete_article", args=[self.article.pk])
            ).status_code,
            403,
        )
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Public article")

    def test_only_journalist_creates_and_author_cannot_be_forged(self):
        payload = {"title": "New", "content": "Text", "author": self.other.pk}
        self.assertEqual(
            self.api(self.editor)
            .post(reverse("api_create_article"), payload)
            .status_code,
            403,
        )
        response = self.api(self.owner).post(
            reverse("api_create_article"), payload
        )
        self.assertEqual(response.status_code, 201)
        created = Article.objects.get(pk=response.data["id"])
        self.assertEqual(created.author, self.owner)
        self.assertFalse(created.approved)

    def test_journalist_cannot_self_approve_on_create_or_update(self):
        api = self.api(self.owner)
        self.assertEqual(
            api.post(
                reverse("api_create_article"),
                {"title": "New", "content": "Text", "approved": True},
            ).status_code,
            400,
        )
        self.assertEqual(
            api.patch(
                reverse("api_update_article", args=[self.pending.pk]),
                {"approved": True},
            ).status_code,
            400,
        )
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.approved)

    def test_journalist_cannot_modify_another_authors_article(self):
        api = self.api(self.other)
        self.assertEqual(
            api.patch(
                reverse("api_update_article", args=[self.article.pk]),
                {"content": "Bad"},
            ).status_code,
            403,
        )
        self.assertEqual(
            api.delete(
                reverse("api_delete_article", args=[self.article.pk])
            ).status_code,
            403,
        )

    def test_own_api_edit_resets_approval_and_preserves_author(self):
        old_time = self.article.updated_at
        response = self.api(self.owner).patch(
            reverse("api_update_article", args=[self.article.pk]),
            {"content": "Revised", "author": self.other.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertFalse(self.article.approved)
        self.assertEqual(self.article.author, self.owner)
        self.assertGreater(self.article.updated_at, old_time)

    def test_editor_can_edit_approve_and_delete_api(self):
        api = self.api(self.editor)
        response = api.patch(
            reverse("api_update_article", args=[self.pending.pk]),
            {"content": "Edited", "approved": True, "author": self.editor.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.pending.refresh_from_db()
        self.assertTrue(self.pending.approved)
        self.assertEqual(self.pending.author, self.owner)
        self.assertEqual(
            api.delete(
                reverse("api_delete_article", args=[self.pending.pk])
            ).status_code,
            204,
        )
        self.assertFalse(Article.objects.filter(pk=self.pending.pk).exists())

    def test_owner_can_delete_api(self):
        self.assertEqual(
            self.api(self.owner)
            .delete(reverse("api_delete_article", args=[self.pending.pk]))
            .status_code,
            204,
        )

    def test_api_publisher_assignment_is_enforced(self):
        api = self.api(self.other)
        self.assertEqual(
            api.post(
                reverse("api_create_article"),
                {
                    "title": "New",
                    "content": "Text",
                    "publisher": self.publisher.pk,
                },
            ).status_code,
            400,
        )
        api = self.api(self.owner)
        self.assertEqual(
            api.post(
                reverse("api_create_article"),
                {
                    "title": "New",
                    "content": "Text",
                    "publisher": self.publisher.pk,
                },
            ).status_code,
            201,
        )
        self.assertEqual(
            api.patch(
                reverse("api_update_article", args=[self.pending.pk]),
                {"publisher": self.unassigned.pk},
            ).status_code,
            400,
        )

    def test_drafts_are_hidden_from_public_readers_and_other_journalists(self):
        for user in (None, self.reader, self.other):
            with self.subTest(user=user):
                api = self.api(user)
                self.assertEqual(
                    api.get(
                        reverse("api_detail", args=[self.pending.pk])
                    ).status_code,
                    404,
                )
                ids = [
                    row["id"] for row in api.get(reverse("api_articles")).data
                ]
                self.assertNotIn(self.pending.pk, ids)
                self.assertIn(self.article.pk, ids)
        for user in (self.owner, self.editor):
            self.assertEqual(
                self.api(user)
                .get(reverse("api_detail", args=[self.pending.pk]))
                .status_code,
                200,
            )

    def test_web_dashboard_permissions(self):
        for user in (self.reader, self.owner, self.editor):
            self.login(user)
            for role in ("reader", "journalist", "editor"):
                with self.subTest(user=user, dashboard=role):
                    self.assertEqual(
                        self.client.get(
                            reverse(role + "_dashboard")
                        ).status_code,
                        200 if user.role == role else 403,
                    )

    def test_web_article_restrictions(self):
        for user in (self.reader, self.other):
            self.login(user)
            self.assertEqual(
                self.client.get(
                    reverse("article_detail", args=[self.pending.pk])
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("edit_article", args=[self.pending.pk]),
                    {"title": "Attack", "content": "No"},
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("delete_article", args=[self.pending.pk])
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("approve_article", args=[self.pending.pk])
                ).status_code,
                403,
            )
        for user in (self.reader, self.editor):
            self.login(user)
            self.assertEqual(
                self.client.post(
                    reverse("create_article"), {"title": "No", "content": "No"}
                ).status_code,
                403,
            )

    def test_web_article_edit_requires_reapproval(self):
        self.login(self.owner)
        response = self.client.post(
            reverse("edit_article", args=[self.article.pk]),
            {
                "title": "Revised",
                "content": "Revised",
                "publisher": self.publisher.pk,
                "approved": True,
                "author": self.other.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertFalse(self.article.approved)
        self.assertEqual(self.article.author, self.owner)
        self.login(self.editor)
        self.assertEqual(
            self.client.post(
                reverse("approve_article", args=[self.article.pk])
            ).status_code,
            302,
        )
        self.article.refresh_from_db()
        self.assertTrue(self.article.approved)

    def test_get_does_not_approve_or_delete(self):
        self.login(self.editor)
        for name, pk in [
            ("approve_article", self.pending.pk),
            ("delete_article", self.article.pk),
            ("delete_newsletter", self.newsletter.pk),
        ]:
            self.assertEqual(
                self.client.get(reverse(name, args=[pk])).status_code, 405
            )
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.approved)
        self.assertTrue(
            Newsletter.objects.filter(pk=self.newsletter.pk).exists()
        )

    def test_newsletter_create_permissions_and_ownership(self):
        payload = {
            "title": "New weekly",
            "description": "News",
            "author": self.other.pk,
            "articles": [self.article.pk],
        }
        for user in (self.reader, self.editor):
            self.login(user)
            self.assertEqual(
                self.client.get(reverse("create_newsletter")).status_code, 403
            )
            self.assertEqual(
                self.client.post(
                    reverse("create_newsletter"), payload
                ).status_code,
                403,
            )
        self.login(self.owner)
        self.assertEqual(
            self.client.post(
                reverse("create_newsletter"), payload
            ).status_code,
            302,
        )
        newsletter = Newsletter.objects.get(title="New weekly")
        self.assertEqual(newsletter.author, self.owner)
        self.assertEqual(list(newsletter.articles.all()), [self.article])

    def test_newsletter_owner_and_editor_edit_but_cannot_change_author(self):
        for user in (self.owner, self.editor):
            self.login(user)
            self.assertEqual(
                self.client.get(
                    reverse("edit_newsletter", args=[self.newsletter.pk])
                ).status_code,
                200,
            )
            response = self.client.post(
                reverse("edit_newsletter", args=[self.newsletter.pk]),
                {
                    "title": "Edited",
                    "description": "Changed",
                    "author": self.other.pk,
                },
            )
            self.assertEqual(response.status_code, 302)
            self.newsletter.refresh_from_db()
            self.assertEqual(self.newsletter.author, self.owner)
            self.assertEqual(self.newsletter.title, "Edited")

    def test_newsletter_nonowners_cannot_modify(self):
        for user in (self.reader, self.other):
            self.login(user)
            self.assertEqual(
                self.client.get(
                    reverse("edit_newsletter", args=[self.newsletter.pk])
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("edit_newsletter", args=[self.newsletter.pk]),
                    {"title": "No", "description": "No"},
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("delete_newsletter", args=[self.newsletter.pk])
                ).status_code,
                403,
            )
        self.newsletter.refresh_from_db()
        self.assertEqual(self.newsletter.title, "Weekly")

    def test_newsletter_owner_and_editor_delete(self):
        for user in (self.owner, self.editor):
            newsletter = Newsletter.objects.create(
                title="Disposable", description="News", author=self.owner
            )
            self.login(user)
            self.assertEqual(
                self.client.post(
                    reverse("delete_newsletter", args=[newsletter.pk])
                ).status_code,
                302,
            )
            self.assertFalse(
                Newsletter.objects.filter(pk=newsletter.pk).exists()
            )

    def test_legacy_newsletters_are_editor_managed_until_assigned(self):
        legacy = Newsletter.objects.create(
            title="Legacy", description="Existing"
        )
        self.login(self.owner)
        self.assertEqual(
            self.client.post(
                reverse("delete_newsletter", args=[legacy.pk])
            ).status_code,
            403,
        )
        self.login(self.editor)
        self.assertEqual(
            self.client.get(
                reverse("edit_newsletter", args=[legacy.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                reverse("delete_newsletter", args=[legacy.pk])
            ).status_code,
            302,
        )

    def test_newsletter_rejects_unapproved_articles_and_unassigned_publisher(
        self,
    ):
        self.login(self.owner)
        for extra in (
            {"articles": [self.pending.pk]},
            {"publisher": self.unassigned.pk},
        ):
            response = self.client.post(
                reverse("create_newsletter"),
                {"title": "Invalid", "description": "No", **extra},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertFalse(Newsletter.objects.filter(title="Invalid").exists())

    def test_newsletter_buttons_match_roles(self):
        for user in (self.reader, self.owner, self.other, self.editor):
            self.login(user)
            response = self.client.get(reverse("newsletter_list"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Weekly")
            self.assertEqual(
                reverse("create_newsletter") in response.content.decode(),
                user.role == "journalist",
            )
            self.assertEqual(
                reverse("edit_newsletter", args=[self.newsletter.pk])
                in response.content.decode(),
                user in (self.owner, self.editor),
            )
            self.assertEqual(
                reverse("delete_newsletter", args=[self.newsletter.pk])
                in response.content.decode(),
                user in (self.owner, self.editor),
            )

    def test_newsletter_hides_articles_returned_to_draft(self):
        self.article.approved = False
        self.article.save()
        self.login(self.reader)
        self.assertNotContains(
            self.client.get(reverse("newsletter_list")), "Public article"
        )

    def test_reader_subscribe_unsubscribe_is_idempotent_and_personal(self):
        self.login(self.reader)
        for kind, target, relation in [
            ("publisher", self.publisher, self.reader.subscribed_publishers),
            ("journalist", self.owner, self.reader.subscribed_journalists),
        ]:
            for action, count in [
                ("subscribe", 1),
                ("subscribe", 1),
                ("unsubscribe", 0),
                ("unsubscribe", 0),
            ]:
                response = self.client.post(
                    reverse("subscriptions"),
                    {
                        "kind": kind,
                        "target_id": target.pk,
                        "action": action,
                        "user_id": self.other.pk,
                    },
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(relation.count(), count)
        self.assertEqual(self.other.subscribed_publishers.count(), 0)
        self.assertEqual(self.other.subscribed_journalists.count(), 0)

    def test_subscription_page_buttons_navigation_and_feed(self):
        self.login(self.reader)
        self.assertContains(
            self.client.get(reverse("reader_dashboard")),
            "Manage Subscriptions",
        )
        self.assertContains(
            self.client.get(reverse("subscriptions")),
            "Subscribe to Daily News",
        )
        self.reader.subscribed_publishers.add(self.publisher)
        self.assertContains(
            self.client.get(reverse("subscriptions")),
            "Unsubscribe from Daily News",
        )
        response = self.client.get(
            reverse("reader_dashboard"), {"feed": "subscribed"}
        )
        self.assertContains(response, self.article.title)
        self.assertNotContains(response, self.pending.title)
        self.assertNotContains(response, self.independent.title)

    def test_subscription_access_and_invalid_targets(self):
        self.assertEqual(
            self.client.get(reverse("subscriptions")).status_code, 302
        )
        for user in (self.owner, self.editor):
            self.login(user)
            self.assertEqual(
                self.client.get(reverse("subscriptions")).status_code, 403
            )
            self.assertEqual(
                self.client.post(
                    reverse("subscriptions"),
                    {
                        "kind": "publisher",
                        "target_id": self.publisher.pk,
                        "action": "subscribe",
                    },
                ).status_code,
                403,
            )
            self.assertEqual(
                self.api(user)
                .get(reverse("api_subscribed_articles"))
                .status_code,
                403,
            )
        self.login(self.reader)
        for target in (self.reader, self.editor):
            self.assertEqual(
                self.client.post(
                    reverse("subscriptions"),
                    {
                        "kind": "journalist",
                        "target_id": target.pk,
                        "action": "subscribe",
                    },
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.post(
                reverse("subscriptions"),
                {
                    "kind": "publisher",
                    "target_id": "bad",
                    "action": "subscribe",
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                reverse("subscriptions"),
                {
                    "kind": "publisher",
                    "target_id": self.publisher.pk,
                    "action": "erase",
                },
            ).status_code,
            400,
        )
        self.client.get(
            reverse("subscriptions"),
            {
                "kind": "publisher",
                "target_id": self.publisher.pk,
                "action": "subscribe",
            },
        )
        self.assertFalse(self.reader.subscribed_publishers.exists())

    def test_subscription_api_filters_and_deduplicates(self):
        self.reader.subscribed_publishers.add(self.publisher)
        self.reader.subscribed_journalists.add(self.owner)
        response = self.api(self.reader).get(
            reverse("api_subscribed_articles")
        )
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [row["id"] for row in response.data],
            [self.article.pk, self.independent.pk],
        )
        self.reader.subscribed_publishers.clear()
        response = self.api(self.reader).get(
            reverse("api_subscribed_articles")
        )
        self.assertEqual(
            [row["id"] for row in response.data], [self.independent.pk]
        )
        self.reader.subscribed_journalists.clear()
        self.assertEqual(
            self.api(self.reader).get(reverse("api_subscribed_articles")).data,
            [],
        )

    def test_csrf_is_required_for_web_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.reader)
        self.assertEqual(
            client.post(
                reverse("subscriptions"),
                {
                    "kind": "publisher",
                    "target_id": self.publisher.pk,
                    "action": "subscribe",
                },
            ).status_code,
            403,
        )
        client.force_login(self.editor)
        self.assertEqual(
            client.post(
                reverse("delete_article", args=[self.article.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            client.post(
                reverse("delete_newsletter", args=[self.newsletter.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            client.post(
                reverse("approve_article", args=[self.pending.pk])
            ).status_code,
            403,
        )

    def test_registration_cannot_grant_editor_or_staff_privileges(self):
        payload = {
            "username": "new-account",
            "email": "new@example.com",
            "password1": "Unusual-pass-482",
            "password2": "Unusual-pass-482",
            "role": "editor",
            "is_staff": True,
        }
        self.assertEqual(
            self.client.post(reverse("register"), payload).status_code, 200
        )
        self.assertFalse(
            CustomUser.objects.filter(username="new-account").exists()
        )
        payload["role"] = "reader"
        self.assertEqual(
            self.client.post(reverse("register"), payload).status_code, 302
        )
        user = CustomUser.objects.get(username="new-account")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(payload["password1"]))

    def test_jwt_login_authenticates_real_requests(self):
        api = APIClient()
        response = api.post(
            reverse("token_obtain_pair"),
            {"username": "reader", "password": "Test-pass-42"},
        )
        self.assertEqual(response.status_code, 200)
        api.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(
            api.get(reverse("api_subscribed_articles")).status_code, 200
        )
        self.assertEqual(
            api.post(
                reverse("api_create_article"), {"title": "No", "content": "No"}
            ).status_code,
            403,
        )
        self.assertEqual(
            api.post(
                reverse("token_refresh"), {"refresh": response.data["refresh"]}
            ).status_code,
            200,
        )

    def test_publisher_management_is_editor_only(self):
        for user in (self.reader, self.owner):
            self.login(user)
            self.assertEqual(
                self.client.get(reverse("publisher_list")).status_code, 403
            )
            self.assertEqual(
                self.client.post(
                    reverse("create_publisher"), {"name": "Forbidden"}
                ).status_code,
                403,
            )
            self.assertEqual(
                self.client.post(
                    reverse("edit_publisher", args=[self.publisher.pk]),
                    {"name": "Forbidden"},
                ).status_code,
                403,
            )
        self.login(self.editor)
        self.assertEqual(
            self.client.post(
                reverse("create_publisher"),
                {
                    "name": "Allowed",
                    "editors": [self.editor.pk],
                    "journalists": [self.owner.pk],
                },
            ).status_code,
            302,
        )
        bad = self.client.post(
            reverse("create_publisher"),
            {"name": "Invalid", "editors": [self.reader.pk]},
        )
        self.assertTrue(bad.context["form"].errors)

    def test_approval_email_once_after_commit(self):
        self.reader.subscribed_journalists.add(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            self.pending.approved = True
            self.pending.save()
            self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.reader.email])
        with self.captureOnCommitCallbacks(execute=True):
            self.pending.content = "Editorial correction"
            self.pending.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_no_approval_email_when_transaction_rolls_back(self):
        self.reader.subscribed_journalists.add(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.pending.approved = True
                    self.pending.save()
                    raise ValueError("Rollback")
            except ValueError:
                pass
        self.assertEqual(len(mail.outbox), 0)

    def test_email_filters_roles_deduplicates_and_keeps_addresses_private(
        self,
    ):
        duplicate = CustomUser.objects.create_user(
            "duplicate", role="reader", email=self.reader.email
        )
        second = CustomUser.objects.create_user(
            "second", role="reader", email="second@example.com"
        )
        self.editor.email = "editor@example.com"
        self.editor.save()
        for user in (self.reader, duplicate, second):
            user.subscribed_publishers.add(self.publisher)
        CustomUser.subscribed_publishers.through.objects.create(
            customuser_id=self.editor.pk, publisher_id=self.publisher.pk
        )
        self.pending.publisher = self.publisher
        with self.captureOnCommitCallbacks(execute=True):
            self.pending.approved = True
            self.pending.save()
        self.assertEqual(len(mail.outbox), 2)
        self.assertCountEqual(
            [message.to for message in mail.outbox],
            [[self.reader.email], [second.email]],
        )

    def test_anonymous_newsletter_and_dashboard_requests_require_login(self):
        for name, args in [
            ("newsletter_list", []),
            ("create_newsletter", []),
            ("edit_newsletter", [self.newsletter.pk]),
            ("delete_newsletter", [self.newsletter.pk]),
            ("editor_dashboard", []),
        ]:
            self.assertEqual(
                self.client.get(reverse(name, args=args)).status_code, 302
            )
            self.assertEqual(
                self.client.post(reverse(name, args=args), {}).status_code, 302
            )

    def test_web_publisher_assignment_and_owner_delete(self):
        self.login(self.other)
        response = self.client.post(
            reverse("create_article"),
            {
                "title": "Invalid",
                "content": "No",
                "publisher": self.publisher.pk,
            },
        )
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Article.objects.filter(title="Invalid").exists())
        self.login(self.owner)
        self.assertEqual(
            self.client.post(
                reverse("delete_article", args=[self.pending.pk])
            ).status_code,
            302,
        )
        self.assertFalse(Article.objects.filter(pk=self.pending.pk).exists())

    def test_approval_email_can_be_sent_after_resubmission(self):
        self.reader.subscribed_journalists.add(self.owner)
        for approved in (True, False, True):
            with self.captureOnCommitCallbacks(execute=True):
                self.pending.approved = approved
                self.pending.save()
        self.assertEqual(len(mail.outbox), 2)

    def test_editor_html_update_preserves_author_and_approval(self):
        self.login(self.editor)
        response = self.client.post(
            reverse("edit_article", args=[self.article.pk]),
            {
                "title": "Correction",
                "content": "Updated",
                "author": self.editor.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertEqual(self.article.author, self.owner)
        self.assertTrue(self.article.approved)
