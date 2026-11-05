"""Issue a personal API token (for /api/v1/me/) to a user.

Tokens are not shown in the app. This prints a new one once; only its hash is stored, and the user's
previous token stops working.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Issue a new personal API token for USERNAME (revokes the previous one) and print it once."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, username, **options):
        user = get_user_model()._default_manager.select_related("profile").filter(username=username).first()
        if user is None:
            raise CommandError(f"No user named {username!r}.")
        token = user.profile.issue_api_token()
        self.stdout.write(token)
        self.stderr.write("Store it now; it can't be shown again. Use it as: Authorization: Bearer <token>")
