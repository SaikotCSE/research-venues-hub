"""Store personal API tokens as SHA-256 hashes.

Existing tokens are hashed in place, so a token someone already copied keeps working. The plain values are gone
afterwards, so this can't be reversed.
"""

import hashlib

from django.db import migrations, models

import accounts.models


def hash_existing_tokens(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    for profile in UserProfile.objects.only("pk", "api_token").iterator():
        if len(profile.api_token) != 64:  # plain tokens are 32 characters; skip anything already hashed
            profile.api_token = hashlib.sha256(profile.api_token.encode()).hexdigest()
            profile.save(update_fields=["api_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_email_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="api_token",
            field=models.CharField(
                default=accounts.models._hashed_token,
                help_text="SHA-256 of the personal API token; the token itself is never stored or shown.",
                max_length=64,
                unique=True,
            ),
        ),
        migrations.RunPython(hash_existing_tokens, migrations.RunPython.noop),
    ]
