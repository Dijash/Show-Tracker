import sys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from tracker.email_service import send_user_monthly_digest, send_all_monthly_digests


class Command(BaseCommand):
    help = 'Dispatches monthly TV progress update emails to registered users via SMTP.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Target a specific user by username or email address.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate email rendering and recipient processing without sending SMTP messages.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sending digest even if the user has 0 shows tracked.',
        )

    def handle(self, *args, **options):
        target_user = options.get('user')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        mode_str = "[DRY-RUN MODE] " if dry_run else ""
        self.stdout.write(f"{mode_str}Starting monthly show updates email dispatch...")

        if target_user:
            # Single user targeted
            user = (
                User.objects.filter(username__iexact=target_user).first()
                or User.objects.filter(email__iexact=target_user).first()
            )
            if not user:
                raise CommandError(f"User '{target_user}' not found.")

            self.stdout.write(f"Targeting single user: {user.username} <{user.email}>")
            success, msg = send_user_monthly_digest(user, dry_run=dry_run, force=force)

            if success:
                self.stdout.write(self.style.SUCCESS(f"SUCCESS: {msg}"))
            else:
                self.stdout.write(self.style.WARNING(f"SKIPPED/FAILED: {msg}"))
        else:
            # All registered users
            results = send_all_monthly_digests(dry_run=dry_run, force=force)
            
            self.stdout.write("--------------------------------------------------")
            self.stdout.write(f"Total candidate users with email: {results['total_candidates']}")
            self.stdout.write(f"Successfully processed / sent:   {results['sent']}")
            self.stdout.write(f"Skipped (no shows/empty):         {results['skipped']}")
            self.stdout.write(f"Failed deliveries:                {results['failed']}")
            self.stdout.write("--------------------------------------------------")

            for detail in results['details']:
                status_label = "[SENT]" if detail['success'] else "[SKIP/FAIL]"
                self.stdout.write(f"  {status_label} {detail['user']} ({detail['email']}): {detail['message']}")

            if results['failed'] == 0:
                self.stdout.write(self.style.SUCCESS(f"{mode_str}Monthly updates completed successfully."))
            else:
                self.stdout.write(self.style.WARNING(f"{mode_str}Monthly updates completed with {results['failed']} failures."))
