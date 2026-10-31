import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Bookmarks may now belong to a user; the old session key becomes ``anon_key`` (data preserved)."""

    dependencies = [
        ("venues", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="venuebookmark", name="uniq_bookmark_session_venue"),
        migrations.RenameField(model_name="venuebookmark", old_name="session_key", new_name="anon_key"),
        migrations.AlterField(model_name="venuebookmark", name="anon_key", field=models.CharField(blank=True, db_index=True, max_length=64)),
        migrations.AddField(
            model_name="venuebookmark", name="user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="bookmarks", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(model_name="venuebookmark", constraint=models.UniqueConstraint(condition=models.Q(("user__isnull", False)), fields=("user", "venue"), name="uniq_bookmark_user_venue")),
        migrations.AddConstraint(model_name="venuebookmark", constraint=models.UniqueConstraint(condition=models.Q(("user__isnull", True)), fields=("anon_key", "venue"), name="uniq_bookmark_anon_venue")),
    ]
