"""Create or update the superuser from environment variables at deploy time.

Reads ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD (python-decouple). Idempotent:
- if the user does not exist, creates a superuser
- if it exists, ensures is_staff/is_superuser and (optionally) resets the password
Silently no-ops when ADMIN_USERNAME or ADMIN_PASSWORD is unset (e.g. local dev).
"""
from decouple import config
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ensure the admin superuser exists (from ADMIN_* env vars).'

    def handle(self, *args, **opts):
        username = config('ADMIN_USERNAME', default='').strip()
        password = config('ADMIN_PASSWORD', default='')
        email = config('ADMIN_EMAIL', default='').strip()

        if not username or not password:
            self.stdout.write('ensure_admin: ADMIN_USERNAME/ADMIN_PASSWORD unset — skipping.')
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username, defaults={'email': email}
        )
        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        # Always sync the password so a rotated env var takes effect on redeploy.
        user.set_password(password)
        user.save()

        # Give the admin a bank profile so role-aware code has something to read.
        try:
            from src.apps.users.models import Profile, ROLE_BANK
            Profile.objects.get_or_create(user=user, defaults={'role': ROLE_BANK})
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(
            f"ensure_admin: superuser '{username}' {'created' if created else 'updated'}."
        ))
