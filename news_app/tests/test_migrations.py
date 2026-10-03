"""Test upgrades with existing newsletter data and relationships."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class NewsletterOwnershipMigrationTests(TransactionTestCase):
    def test_existing_newsletter_and_article_links_survive_upgrade(self):
        old_target = [("news_app", "0003_newsletter_articles")]
        latest_target = [("news_app", "0005_role_groups")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            User = old_apps.get_model("news_app", "CustomUser")
            Article = old_apps.get_model("news_app", "Article")
            Newsletter = old_apps.get_model("news_app", "Newsletter")
            author = User.objects.create(
                username="legacy-journalist", role="journalist"
            )
            Group = old_apps.get_model("auth", "Group")
            custom = Group.objects.create(name="Preserved unrelated group")
            wrong, _ = Group.objects.get_or_create(name="Reader")
            author.groups.add(custom, wrong)
            Publisher = old_apps.get_model("news_app", "Publisher")
            publisher = Publisher.objects.create(name="Existing publisher")
            author.subscribed_publishers.add(publisher)
            article = Article.objects.create(
                title="Existing article", content="Preserve", author=author
            )
            newsletter = Newsletter.objects.create(
                title="Existing newsletter", description="Keep this"
            )
            newsletter.articles.add(article)
            executor = MigrationExecutor(connection)
            executor.migrate(latest_target)
            new_apps = executor.loader.project_state(latest_target).apps
            migrated = new_apps.get_model(
                "news_app", "Newsletter"
            ).objects.get(pk=newsletter.pk)
            migrated_user = new_apps.get_model(
                "news_app", "CustomUser"
            ).objects.get(pk=author.pk)
            self.assertCountEqual(
                migrated_user.groups.values_list("name", flat=True),
                ["Journalist", "Preserved unrelated group"],
            )
            self.assertFalse(migrated_user.subscribed_publishers.exists())
            self.assertTrue(
                new_apps.get_model("news_app", "Article")
                .objects.filter(pk=article.pk)
                .exists()
            )
            self.assertIsNone(migrated.author_id)
            self.assertEqual(migrated.title, "Existing newsletter")
            self.assertEqual(migrated.description, "Keep this")
            self.assertEqual(
                list(migrated.articles.values_list("pk", flat=True)),
                [article.pk],
            )
        finally:
            MigrationExecutor(connection).migrate(latest_target)
