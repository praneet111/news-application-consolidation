"""Add nullable ownership without guessing authors of existing newsletters."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("news_app", "0003_newsletter_articles")]
    operations = [
        migrations.AddField(
            model_name="newsletter",
            name="author",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="newsletters",
                null=True,
                blank=True,
            ),
        ),
    ]
