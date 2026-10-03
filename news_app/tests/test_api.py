from django.test import TestCase

from news_app.models import (
    Article,
    CustomUser,
    Publisher,
)


class UserModelTest(TestCase):
    """
    Test custom user model.
    """

    def test_create_reader_user(self):
        """
        Test reader user creation.
        """

        user = CustomUser.objects.create_user(
            username="reader1", password="password123", role="reader"
        )

        self.assertEqual(user.role, "reader")


class PublisherTest(TestCase):
    """
    Test publisher model.
    """

    def test_create_publisher(self):
        """
        Test publisher creation.
        """

        publisher = Publisher.objects.create(name="BBC")

        self.assertEqual(publisher.name, "BBC")


class ArticleTest(TestCase):
    """
    Test article model.
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="journalist1", password="password123", role="journalist"
        )

        self.publisher = Publisher.objects.create(name="CNN")

    def test_create_article(self):
        """
        Test article creation.
        """

        article = Article.objects.create(
            title="Breaking News",
            content="Test article content",
            author=self.user,
            publisher=self.publisher,
            approved=True,
        )

        self.assertEqual(article.title, "Breaking News")

    def test_article_approval(self):
        """
        Test article approval.
        """

        article = Article.objects.create(
            title="News",
            content="Content",
            author=self.user,
            publisher=self.publisher,
            approved=True,
        )

        self.assertTrue(article.approved)


class HomepageTest(TestCase):
    """
    Test homepage response.
    """

    def test_homepage_status_code(self):
        """
        Homepage should return status code 200.
        """

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)


class APITest(TestCase):
    """
    Test API endpoint.
    """

    def test_api_status_code(self):
        """
        API endpoint should return 200.
        """

        response = self.client.get("/api/articles/")

        self.assertEqual(response.status_code, 200)
