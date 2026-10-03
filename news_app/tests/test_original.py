from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from news_app.models import Article, CustomUser, Newsletter, Publisher


class NewsApplicationTests(TestCase):
    """
    Automated tests for the news application.
    """

    def setUp(self):
        """
        Create users, publisher, articles, and API client for tests.
        """

        self.reader = CustomUser.objects.create_user(
            username="reader_test",
            password="password123",
            role="reader",
            email="reader@example.com",
        )

        self.journalist = CustomUser.objects.create_user(
            username="journalist_test",
            password="password123",
            role="journalist",
            email="journalist@example.com",
        )

        self.editor = CustomUser.objects.create_user(
            username="editor_test",
            password="password123",
            role="editor",
            email="editor@example.com",
        )

        self.publisher = Publisher.objects.create(name="Test Publisher")

        self.publisher.journalists.add(self.journalist)

        self.article = Article.objects.create(
            title="Approved Article",
            content="Approved article content",
            author=self.journalist,
            publisher=self.publisher,
            approved=True,
        )

        self.pending_article = Article.objects.create(
            title="Pending Article",
            content="Pending article content",
            author=self.journalist,
            publisher=self.publisher,
            approved=False,
        )

        self.client = APIClient()

    def test_reader_can_view_approved_articles(self):
        """
        Reader can access approved articles through API.
        """

        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, 200)

    def test_subscribed_articles_endpoint(self):
        """
        Reader can retrieve articles from subscribed publishers.
        """

        self.reader.subscribed_publishers.add(self.publisher)

        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/articles/subscribed/")

        self.assertEqual(response.status_code, 200)

        self.assertGreaterEqual(len(response.data), 1)

    def test_journalist_can_create_article_api(self):
        """
        Journalist can create an article through API.
        """

        self.client.force_authenticate(user=self.journalist)

        response = self.client.post(
            "/api/articles/create/",
            {
                "title": "API Article",
                "content": "API created article",
                "author": self.journalist.id,
                "publisher": self.publisher.id,
                "approved": False,
            },
        )

        self.assertIn(response.status_code, [200, 201])

    def test_editor_can_approve_article(self):
        """
        Editor approval updates article status.
        """

        self.client.force_login(self.editor)

        response = self.client.post(
            f"/articles/{self.pending_article.id}/approve/"
        )

        self.pending_article.refresh_from_db()

        self.assertTrue(self.pending_article.approved)

        self.assertEqual(response.status_code, 302)

    def test_newsletter_can_be_created(self):
        """
        Newsletter model creates successfully.
        """

        newsletter = Newsletter.objects.create(
            title="Weekly News",
            description="Weekly newsletter",
            publisher=self.publisher,
        )

        self.assertEqual(newsletter.title, "Weekly News")

    @patch("news_app.signals.send_mail")
    def test_signal_logic_runs_on_article_approval(self, mock_send_mail):
        """Approval sends email after the database transaction commits."""
        self.reader.subscribed_publishers.add(self.publisher)
        with self.captureOnCommitCallbacks(execute=True):
            self.pending_article.approved = True
            self.pending_article.save()
        mock_send_mail.assert_called_once()
