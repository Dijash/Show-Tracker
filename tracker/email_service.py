import logging
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from .models import Show

logger = logging.getLogger('tracker.email')


def generate_user_digest_data(user):
    """
    Compiles monthly metrics and categorized show collections for a given user.
    """
    shows = list(Show.objects.filter(user=user).prefetch_related('seasons').all())

    total_shows = len(shows)
    watching_shows = []
    completed_shows = []
    plan_to_watch_shows = []
    dropped_shows = []

    total_episodes_watched = 0
    total_episodes_available = 0

    for show in shows:
        watched = show.episodes_watched
        total = show.total_episodes
        total_episodes_watched += watched
        total_episodes_available += total

        progress_pct = int((watched / total * 100)) if total > 0 else 0
        seasons_list = list(show.seasons.all())

        # Determine current active season and next episode
        current_season_info = None
        for s in seasons_list:
            if s.episodes_watched < s.total_episodes:
                current_season_info = {
                    'season_number': s.season_number,
                    'episodes_watched': s.episodes_watched,
                    'total_episodes': s.total_episodes,
                    'next_episode': s.episodes_watched + 1,
                }
                break

        show_item = {
            'id': show.id,
            'title': show.title,
            'status': show.status,
            'rating': show.rating,
            'platform': show.platform,
            'genres': show.genres,
            'total_seasons': show.total_seasons,
            'episodes_watched': watched,
            'total_episodes': total,
            'progress_pct': progress_pct,
            'current_season_info': current_season_info,
            'updated_at': show.updated_at,
        }

        if show.status == Show.STATUS_WATCHING:
            watching_shows.append(show_item)
        elif show.status == Show.STATUS_COMPLETED:
            completed_shows.append(show_item)
        elif show.status == Show.STATUS_PLAN_TO_WATCH:
            plan_to_watch_shows.append(show_item)
        elif show.status == Show.STATUS_DROPPED:
            dropped_shows.append(show_item)

    # Sort watching shows by last updated
    watching_shows.sort(key=lambda x: x['updated_at'], reverse=True)
    completed_shows.sort(key=lambda x: x['updated_at'], reverse=True)

    overall_completion_pct = int((total_episodes_watched / total_episodes_available * 100)) if total_episodes_available > 0 else 0
    now = datetime.now()
    month_name = now.strftime('%B %Y')

    return {
        'user': user,
        'username': user.username,
        'email': user.email,
        'month_name': month_name,
        'total_shows': total_shows,
        'watching_count': len(watching_shows),
        'completed_count': len(completed_shows),
        'plan_to_watch_count': len(plan_to_watch_shows),
        'dropped_count': len(dropped_shows),
        'total_episodes_watched': total_episodes_watched,
        'total_episodes_available': total_episodes_available,
        'overall_completion_pct': overall_completion_pct,
        'watching_shows': watching_shows,
        'completed_shows': completed_shows[:5],  # top 5 recently completed
        'plan_to_watch_shows': plan_to_watch_shows[:5],  # top 5 watchlist
    }


def send_user_monthly_digest(user, dry_run=False, force=False):
    """
    Renders and dispatches the monthly show progress digest email to a single user.
    Returns (success: bool, message: str).
    """
    if not user.email or not user.email.strip():
        logger.warning(f"Skipping monthly digest for user '{user.username}': No registered email address.")
        return False, f"User '{user.username}' does not have an email address."

    data = generate_user_digest_data(user)

    if data['total_shows'] == 0 and not force:
        logger.info(f"Skipping monthly digest for user '{user.username}': 0 shows tracked.")
        return False, f"User '{user.username}' has 0 shows tracked (use force to send anyway)."

    subject = f"[Show Tracker] Monthly TV Progress Digest - {data['month_name']}"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email.strip()]

    try:
        text_content = render_to_string('emails/monthly_digest.txt', data)
        html_content = render_to_string('emails/monthly_digest.html', data)

        if dry_run:
            logger.info(f"[DRY-RUN] Monthly digest rendered for '{user.username}' <{user.email}> ({data['total_shows']} shows).")
            return True, f"[DRY-RUN] Simulated digest for {user.username} ({user.email})."

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        logger.info(f"Successfully sent monthly digest email to '{user.username}' <{user.email}>.")
        return True, f"Monthly digest sent to {user.email}."

    except Exception as e:
        logger.error(f"Failed to send monthly digest to '{user.username}' <{user.email}>: {e}", exc_info=True)
        return False, f"Email delivery failed: {str(e)}"


def send_all_monthly_digests(dry_run=False, force=False):
    """
    Iterates over all active registered users with valid emails and dispatches monthly digests.
    Returns a summary dictionary.
    """
    users = User.objects.filter(is_active=True).exclude(email='').order_by('id')
    results = {
        'total_candidates': users.count(),
        'sent': 0,
        'skipped': 0,
        'failed': 0,
        'details': []
    }

    for user in users:
        success, msg = send_user_monthly_digest(user, dry_run=dry_run, force=force)
        results['details'].append({'user': user.username, 'email': user.email, 'success': success, 'message': msg})
        if success:
            results['sent'] += 1
        elif '0 shows tracked' in msg or 'does not have an email' in msg:
            results['skipped'] += 1
        else:
            results['failed'] += 1

    return results
