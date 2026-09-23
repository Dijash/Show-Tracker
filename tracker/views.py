import json
import logging
import os
import re
import secrets
import time
import urllib.request
import urllib.parse
from functools import wraps
from collections import Counter
import requests
from django.conf import settings
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Show, Season
from .email_service import send_user_monthly_digest

logger = logging.getLogger('tracker.views')

# In-memory external search and details cache to eliminate API buffering
_EXTERNAL_SEARCH_CACHE = {}
_EXTERNAL_DETAILS_CACHE = {}
CACHE_TTL_SECONDS = 3600  # 1 hour cache


def _get_from_cache(cache_dict, key):
    entry = cache_dict.get(key)
    if entry and (time.time() - entry['timestamp'] < CACHE_TTL_SECONDS):
        return entry['data']
    if entry:
        del cache_dict[key]
    return None


def _set_in_cache(cache_dict, key, data):
    # Keep cache size bounded
    if len(cache_dict) > 500:
        oldest_key = min(cache_dict.keys(), key=lambda k: cache_dict[k]['timestamp'])
        del cache_dict[oldest_key]
    cache_dict[key] = {
        'data': data,
        'timestamp': time.time()
    }


def require_user_auth(view_func):
    """Decorator ensuring JSON API endpoints return 401 when unauthenticated."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required. Please log in.'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================

@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect('tracker:index')

    error = None
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            error = 'Please enter both username and password.'
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                    return redirect(next_url)
                return redirect('tracker:index')
            else:
                error = 'Invalid username or password.'

    return render(request, 'auth/login.html', {
        'error': error,
        'next': next_url,
    })


@ensure_csrf_cookie
def register_view(request):
    if request.user.is_authenticated:
        return redirect('tracker:index')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not username:
            error = 'Username is required.'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters long.'
        elif len(username) > 150:
            error = 'Username cannot exceed 150 characters.'
        elif not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            error = 'Username may only contain letters, numbers, dots, dashes, and underscores.'
        elif User.objects.filter(username__iexact=username).exists():
            error = f'Username "{username}" is already taken. Please choose another.'
        elif not password:
            error = 'Password is required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != password_confirm:
            error = 'Passwords do not match.'
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            login(request, user)
            return redirect('tracker:index')

    return render(request, 'auth/register.html', {
        'error': error,
    })


def logout_view(request):
    logout(request)
    return redirect('tracker:login')


def google_oauth_login(request):
    """
    Initiates Google OAuth 2.0 authorization code flow.
    """
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.getenv('GOOGLE_CLIENT_ID', '')
    if not client_id:
        logger.error("Google OAuth login attempted but GOOGLE_CLIENT_ID is not configured.")
        return render(request, 'auth/login.html', {
            'error': 'Google Sign-In is not configured on this server.'
        })

    # Generate cryptographically secure random state to prevent CSRF
    state = secrets.token_urlsafe(32)
    request.session['oauth_google_state'] = state

    # Capture optional next parameter
    next_url = request.GET.get('next', '')
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        request.session['oauth_google_next'] = next_url

    redirect_uri = request.build_absolute_uri(reverse('tracker:google_oauth_callback'))

    params = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': redirect_uri,
        'state': state,
        'prompt': 'select_account',
        'access_type': 'online',
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


def google_oauth_callback(request):
    """
    Handles the OAuth 2.0 authorization callback from Google.
    Exchanges the code for tokens, retrieves profile, and logs in or creates the user.
    """
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.getenv('GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or os.getenv('GOOGLE_CLIENT_SECRET', '')

    next_url = request.session.pop('oauth_google_next', None) or 'tracker:index'
    session_state = request.session.pop('oauth_google_state', None)

    # Check for Google authorization errors (e.g., access_denied)
    google_error = request.GET.get('error')
    if google_error:
        logger.warning(f"Google OAuth authorization returned error: {google_error}")
        return render(request, 'auth/login.html', {
            'error': f'Google authorization was cancelled or failed ({google_error}).'
        })

    # Validate state parameter for CSRF mitigation
    returned_state = request.GET.get('state')
    if not session_state or not returned_state or session_state != returned_state:
        logger.warning("Google OAuth state mismatch detected.")
        return render(request, 'auth/login.html', {
            'error': 'Invalid OAuth session state. Please try signing in again.'
        })

    code = request.GET.get('code')
    if not code:
        logger.warning("Google OAuth callback missing authorization code.")
        return render(request, 'auth/login.html', {
            'error': 'Missing authorization code from Google.'
        })

    redirect_uri = request.build_absolute_uri(reverse('tracker:google_oauth_callback'))

    # Exchange authorization code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }

    try:
        token_response = requests.post(token_url, data=token_data, timeout=10)
        if token_response.status_code != 200:
            logger.error(f"Google token exchange failed: {token_response.status_code} - {token_response.text}")
            return render(request, 'auth/login.html', {
                'error': 'Failed to exchange authorization code with Google.'
            })

        token_json = token_response.json()
        access_token = token_json.get('access_token')
        if not access_token:
            return render(request, 'auth/login.html', {
                'error': 'Invalid token response received from Google.'
            })

        # Fetch user profile from Google UserInfo endpoint
        userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)

        if userinfo_response.status_code != 200:
            logger.error(f"Google userinfo request failed: {userinfo_response.status_code} - {userinfo_response.text}")
            return render(request, 'auth/login.html', {
                'error': 'Failed to fetch user profile from Google.'
            })

        user_info = userinfo_response.json()
        email = user_info.get('email', '').strip()
        given_name = user_info.get('given_name', '').strip()
        family_name = user_info.get('family_name', '').strip()

        if not email:
            return render(request, 'auth/login.html', {
                'error': 'Google account does not have an associated email address.'
            })

        # Check if user with this email already exists
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # Generate unique username
            base_username = email.split('@')[0]
            clean_username = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_username)[:140]
            if not clean_username:
                clean_username = 'google_user'

            username = clean_username
            counter = 1
            while User.objects.filter(username__iexact=username).exists():
                suffix = f"_{counter}"
                username = f"{clean_username[:150 - len(suffix)]}{suffix}"
                counter += 1

            user = User.objects.create(
                username=username,
                email=email,
                first_name=given_name[:150],
                last_name=family_name[:150]
            )
            user.set_unusable_password()
            user.save()
            logger.info(f"Created new user '{username}' via Google OAuth.")
        else:
            logger.info(f"Existing user '{user.username}' authenticated via Google OAuth.")

        # Establish authenticated Django session
        login(request, user)

        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
        return redirect('tracker:index')

    except requests.RequestException as e:
        logger.error(f"Network error during Google OAuth flow: {e}")
        return render(request, 'auth/login.html', {
            'error': 'Network error communicating with Google servers. Please try again.'
        })
    except Exception as e:
        logger.error(f"Unexpected error in Google OAuth callback: {e}", exc_info=True)
        return render(request, 'auth/login.html', {
            'error': 'An unexpected error occurred during Google Sign-In.'
        })


# =============================================================================
# STATS & DASHBOARD VIEWS
# =============================================================================

def calculate_global_stats(shows=None, user=None):
    """
    Computes all global metrics in-memory from prefetched shows without executing extra DB queries.
    """
    if shows is None:
        if user and user.is_authenticated:
            shows = list(Show.objects.filter(user=user).prefetch_related('seasons').all())
        else:
            shows = []

    total_shows = len(shows)
    watching_count = 0
    completed_count = 0
    plan_to_watch_count = 0
    on_hold_count = 0
    dropped_count = 0
    total_episodes = 0
    episodes_watched = 0

    for s in shows:
        if s.status == Show.STATUS_WATCHING:
            watching_count += 1
        elif s.status == Show.STATUS_COMPLETED:
            completed_count += 1
        elif s.status == Show.STATUS_PLAN_TO_WATCH:
            plan_to_watch_count += 1
        elif s.status == Show.STATUS_ON_HOLD:
            on_hold_count += 1
        elif s.status == Show.STATUS_DROPPED:
            dropped_count += 1

        total_episodes += s.total_episodes
        episodes_watched += s.episodes_watched

    completion_pct = int(round((episodes_watched / total_episodes * 100))) if total_episodes > 0 else 0
    estimated_hours = int(round((episodes_watched * 45) / 60))

    return {
        'total_shows': total_shows,
        'watching_count': watching_count,
        'completed_count': completed_count,
        'plan_to_watch_count': plan_to_watch_count,
        'on_hold_count': on_hold_count,
        'dropped_count': dropped_count,
        'total_episodes': total_episodes,
        'episodes_watched': episodes_watched,
        'completion_pct': completion_pct,
        'estimated_hours': estimated_hours,
    }


@login_required(login_url='tracker:login')
@ensure_csrf_cookie
def index_view(request):
    shows = list(Show.objects.filter(user=request.user).prefetch_related('seasons').all())

    # Calculate max seasons in memory
    max_seasons = 1
    for show in shows:
        s_count = len(show.seasons.all())
        if s_count > max_seasons:
            max_seasons = s_count
        if show.total_seasons > max_seasons:
            max_seasons = show.total_seasons

    if not shows:
        max_seasons = 4

    season_columns = list(range(1, max_seasons + 1))
    stats = calculate_global_stats(shows, user=request.user)

    # Prepare serializable shows payload with in-memory serialization
    shows_json = json.dumps([s.to_dict() for s in shows])

    context = {
        'shows': shows,
        'max_seasons': max_seasons,
        'season_columns': season_columns,
        'stats': stats,
        'shows_json': shows_json,
    }
    return render(request, 'tracker/index.html', context)


# =============================================================================
# JSON API ENDPOINTS (PER-USER ISOLATED)
# =============================================================================

@require_http_methods(["GET"])
@require_user_auth
def api_get_shows(request):
    shows = list(Show.objects.filter(user=request.user).prefetch_related('seasons').all())
    stats = calculate_global_stats(shows, user=request.user)
    return JsonResponse({
        'success': True,
        'shows': [s.to_dict() for s in shows],
        'stats': stats,
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_create_show(request):
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Show title is required.'}, status=400)

        # Prevent duplicate show entry for this user (case-insensitive)
        if Show.objects.filter(user=request.user, title__iexact=title).exists():
            return JsonResponse({
                'success': False,
                'error': f'A show titled "{title}" already exists in your tracker.'
            }, status=400)

        poster_url = data.get('poster_url', '').strip() or None
        status = data.get('status', Show.STATUS_WATCHING)
        rating = float(data.get('rating', 0.0))
        season_configs = data.get('seasons', [])
        if season_configs and isinstance(season_configs, list):
            total_seasons = len(season_configs)
        else:
            total_seasons = int(data.get('total_seasons', 1))

        release_year = int(data.get('release_year')) if data.get('release_year') else None
        genres = data.get('genres', '').strip()
        platform = data.get('platform', '').strip()
        notes = data.get('notes', '').strip()

        with transaction.atomic():
            show = Show.objects.create(
                user=request.user,
                title=title,
                poster_url=poster_url,
                status=status,
                rating=rating,
                total_seasons=max(1, total_seasons),
                release_year=release_year,
                genres=genres,
                platform=platform,
                notes=notes,
            )

            seasons_to_create = []
            if season_configs and isinstance(season_configs, list):
                for idx, sc in enumerate(season_configs, start=1):
                    tot_eps = max(1, int(sc.get('total_episodes', 10)))
                    eps_w = max(0, min(tot_eps, int(sc.get('episodes_watched', 0))))
                    seasons_to_create.append(
                        Season(
                            show=show,
                            season_number=idx,
                            total_episodes=tot_eps,
                            episodes_watched=eps_w,
                            is_completed=(eps_w >= tot_eps and tot_eps > 0)
                        )
                    )
            else:
                default_episodes = max(1, int(data.get('default_episodes', 10)))
                for s_num in range(1, show.total_seasons + 1):
                    seasons_to_create.append(
                        Season(
                            show=show,
                            season_number=s_num,
                            total_episodes=default_episodes,
                            episodes_watched=0,
                            is_completed=False
                        )
                    )

            if seasons_to_create:
                Season.objects.bulk_create(seasons_to_create)

        # Reload with prefetched seasons for 0-query serialization
        show = Show.objects.prefetch_related('seasons').get(id=show.id, user=request.user)
        stats = calculate_global_stats(user=request.user)
        return JsonResponse({
            'success': True,
            'message': f'Show "{show.title}" added successfully.',
            'show': show.to_dict(),
            'stats': stats,
        })
    except Exception as e:
        logger.exception("Error in api_create_show: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_update_show(request, show_id):
    try:
        data = json.loads(request.body)

        with transaction.atomic():
            show = get_object_or_404(Show, id=show_id, user=request.user)

            if 'title' in data:
                title = data.get('title', '').strip()
                if not title:
                    return JsonResponse({'success': False, 'error': 'Show title cannot be empty.'}, status=400)
                # Prevent duplicate show entry for this user on rename (case-insensitive)
                if Show.objects.filter(user=request.user, title__iexact=title).exclude(id=show_id).exists():
                    return JsonResponse({
                        'success': False,
                        'error': f'Another show titled "{title}" already exists in your tracker.'
                    }, status=400)
                show.title = title

            if 'poster_url' in data:
                show.poster_url = data.get('poster_url', '').strip() or None
            if 'status' in data:
                show.status = data.get('status')
            if 'rating' in data:
                show.rating = float(data.get('rating', 0.0))
            if 'release_year' in data:
                show.release_year = int(data.get('release_year')) if data.get('release_year') else None
            if 'genres' in data:
                show.genres = data.get('genres', '').strip()
            if 'platform' in data:
                show.platform = data.get('platform', '').strip()
            if 'notes' in data:
                show.notes = data.get('notes', '').strip()

            # Update seasons if provided
            if 'seasons' in data and isinstance(data['seasons'], list):
                season_list = data['seasons']
                show.total_seasons = len(season_list)
                show.save()

                # Sync season records efficiently
                existing_seasons = {s.season_number: s for s in show.seasons.all()}
                to_update = []
                to_create = []

                for idx, sc in enumerate(season_list, start=1):
                    tot_eps = max(1, int(sc.get('total_episodes', 10)))
                    eps_w = max(0, min(tot_eps, int(sc.get('episodes_watched', 0))))
                    is_comp = (eps_w >= tot_eps and tot_eps > 0)

                    if idx in existing_seasons:
                        s_obj = existing_seasons[idx]
                        s_obj.total_episodes = tot_eps
                        s_obj.episodes_watched = eps_w
                        s_obj.is_completed = is_comp
                        to_update.append(s_obj)
                    else:
                        to_create.append(
                            Season(
                                show=show,
                                season_number=idx,
                                total_episodes=tot_eps,
                                episodes_watched=eps_w,
                                is_completed=is_comp
                            )
                        )

                if to_update:
                    Season.objects.bulk_update(to_update, ['total_episodes', 'episodes_watched', 'is_completed'])
                if to_create:
                    Season.objects.bulk_create(to_create)

                # Remove deleted excess seasons
                show.seasons.filter(season_number__gt=len(season_list)).delete()
            else:
                show.save()

        show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
        stats = calculate_global_stats(user=request.user)
        return JsonResponse({
            'success': True,
            'message': f'Show "{show.title}" updated successfully.',
            'show': show.to_dict(),
            'stats': stats,
        })
    except Http404:
        return JsonResponse({'success': False, 'error': 'Show not found or access denied.'}, status=404)
    except Exception as e:
        logger.exception("Error in api_update_show for show_id=%s: %s", show_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_delete_show(request, show_id):
    try:
        with transaction.atomic():
            show = get_object_or_404(Show, id=show_id, user=request.user)
            title = show.title
            show.delete()

        stats = calculate_global_stats(user=request.user)
        return JsonResponse({
            'success': True,
            'message': f'Show "{title}" removed.',
            'deleted_id': show_id,
            'stats': stats,
        })
    except Http404:
        return JsonResponse({'success': False, 'error': 'Show not found or access denied.'}, status=404)
    except Exception as e:
        logger.exception("Error in api_delete_show for show_id=%s: %s", show_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_update_season_episode(request, season_id):
    try:
        data = json.loads(request.body)
        episodes_watched = int(data.get('episodes_watched', 0))

        with transaction.atomic():
            season = get_object_or_404(Season.objects.select_related('show'), id=season_id, show__user=request.user)
            season.episodes_watched = max(0, min(season.total_episodes, episodes_watched))
            season.save()

            show_id = season.show_id
            show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)

            # Check if parent show status should be automatically updated
            if show.is_all_completed and show.status != Show.STATUS_COMPLETED:
                show.status = Show.STATUS_COMPLETED
                show.save(update_fields=['status', 'updated_at'])
            elif not show.is_all_completed and show.status == Show.STATUS_PLAN_TO_WATCH and season.episodes_watched > 0:
                show.status = Show.STATUS_WATCHING
                show.save(update_fields=['status', 'updated_at'])
            elif not show.is_all_completed and show.status == Show.STATUS_COMPLETED:
                show.status = Show.STATUS_WATCHING
                show.save(update_fields=['status', 'updated_at'])
            else:
                show.save(update_fields=['updated_at'])

        # Reload clean prefetched show
        show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
        updated_season = next((s for s in show.seasons.all() if s.id == season_id), season)

        stats = calculate_global_stats(user=request.user)
        return JsonResponse({
            'success': True,
            'season': updated_season.to_dict(),
            'show': show.to_dict(),
            'stats': stats,
        })
    except Http404:
        return JsonResponse({'success': False, 'error': 'Season not found or access denied.'}, status=404)
    except Exception as e:
        logger.exception("Error in api_update_season_episode for season_id=%s: %s", season_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_toggle_season_complete(request, season_id):
    try:
        with transaction.atomic():
            season = get_object_or_404(Season.objects.select_related('show'), id=season_id, show__user=request.user)
            if season.episodes_watched >= season.total_episodes:
                season.episodes_watched = 0
            else:
                season.episodes_watched = season.total_episodes
            season.save()

            show_id = season.show_id
            show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
            if show.is_all_completed:
                show.status = Show.STATUS_COMPLETED
            elif show.status == Show.STATUS_COMPLETED and not show.is_all_completed:
                show.status = Show.STATUS_WATCHING
            show.save(update_fields=['status', 'updated_at'])

        # Reload clean prefetched show
        show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
        updated_season = next((s for s in show.seasons.all() if s.id == season_id), season)

        stats = calculate_global_stats(user=request.user)
        return JsonResponse({
            'success': True,
            'season': updated_season.to_dict(),
            'show': show.to_dict(),
            'stats': stats,
        })
    except Http404:
        return JsonResponse({'success': False, 'error': 'Season not found or access denied.'}, status=404)
    except Exception as e:
        logger.exception("Error in api_toggle_season_complete for season_id=%s: %s", season_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_quick_step(request, show_id):
    """Step +1 or -1 episode in current in-progress season with zero query bypasses."""
    try:
        data = json.loads(request.body)
        direction = int(data.get('direction', 1))  # +1 or -1

        with transaction.atomic():
            show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
            seasons = sorted(show.seasons.all(), key=lambda s: s.season_number)
            if not seasons:
                return JsonResponse({'success': False, 'error': 'Show has no seasons.'}, status=400)

            target_season = None
            if direction > 0:
                for s in seasons:
                    if s.episodes_watched < s.total_episodes:
                        target_season = s
                        break
                if not target_season:
                    target_season = seasons[-1]  # all complete, stay at last
                else:
                    target_season.episodes_watched += 1
                    target_season.save()
            else:
                # Step backward
                for s in reversed(seasons):
                    if s.episodes_watched > 0:
                        target_season = s
                        break
                if target_season:
                    target_season.episodes_watched -= 1
                    target_season.save()

            # Refresh in-memory show status
            show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
            if show.is_all_completed:
                show.status = Show.STATUS_COMPLETED
            elif show.status == Show.STATUS_PLAN_TO_WATCH and show.episodes_watched > 0:
                show.status = Show.STATUS_WATCHING
            elif show.status == Show.STATUS_COMPLETED and not show.is_all_completed:
                show.status = Show.STATUS_WATCHING
            show.save(update_fields=['status', 'updated_at'])

        # Final prefetched load
        show = Show.objects.prefetch_related('seasons').get(id=show_id, user=request.user)
        stats = calculate_global_stats(user=request.user)
        return JsonResponse({
            'success': True,
            'show': show.to_dict(),
            'stats': stats,
        })
    except Show.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Show not found or access denied.'}, status=404)
    except Http404:
        return JsonResponse({'success': False, 'error': 'Show not found or access denied.'}, status=404)
    except Exception as e:
        logger.exception("Error in api_quick_step for show_id=%s: %s", show_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_clear_all(request):
    try:
        with transaction.atomic():
            Show.objects.filter(user=request.user).delete()

        stats = calculate_global_stats([], user=request.user)
        return JsonResponse({
            'success': True,
            'message': 'All your shows have been cleared.',
            'shows': [],
            'stats': stats,
        })
    except Exception as e:
        logger.exception("Error in api_clear_all: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["GET"])
@require_user_auth
def api_export_json(request):
    shows = list(Show.objects.filter(user=request.user).prefetch_related('seasons').all())
    stats = calculate_global_stats(shows, user=request.user)
    data = {
        'version': '2.0',
        'username': request.user.username,
        'export_time': stats,
        'shows': [s.to_dict() for s in shows]
    }
    response = HttpResponse(
        json.dumps(data, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="show_tracker_backup_{request.user.username}.json"'
    return response


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_import_json(request):
    try:
        data = json.loads(request.body)
        shows_list = data.get('shows', [])
        imported = 0

        with transaction.atomic():
            for item in shows_list:
                raw_title = item.get('title')
                if not raw_title:
                    continue
                title = str(raw_title).strip()
                if not title:
                    continue

                show = Show.objects.filter(user=request.user, title__iexact=title).first()
                if show:
                    show.title = title
                    show.poster_url = item.get('poster_url') or None
                    show.status = item.get('status', Show.STATUS_WATCHING)
                    show.rating = float(item.get('rating', 0.0))
                    show.release_year = item.get('release_year')
                    show.genres = item.get('genres', '')
                    show.platform = item.get('platform', '')
                    show.notes = item.get('notes', '')
                    show.total_seasons = max(1, int(item.get('total_seasons', len(item.get('seasons', [])) or 1)))
                    show.save()
                else:
                    show = Show.objects.create(
                        user=request.user,
                        title=title,
                        poster_url=item.get('poster_url') or None,
                        status=item.get('status', Show.STATUS_WATCHING),
                        rating=float(item.get('rating', 0.0)),
                        release_year=item.get('release_year'),
                        genres=item.get('genres', ''),
                        platform=item.get('platform', ''),
                        notes=item.get('notes', ''),
                        total_seasons=max(1, int(item.get('total_seasons', len(item.get('seasons', [])) or 1))),
                    )
                # update seasons in bulk
                if 'seasons' in item:
                    show.seasons.all().delete()
                    seasons_to_create = []
                    for s_data in item['seasons']:
                        tot_eps = max(1, int(s_data.get('total_episodes', 10)))
                        eps_w = max(0, int(s_data.get('episodes_watched', 0)))
                        seasons_to_create.append(
                            Season(
                                show=show,
                                season_number=s_data.get('season_number', 1),
                                total_episodes=tot_eps,
                                episodes_watched=eps_w,
                                is_completed=(eps_w >= tot_eps and tot_eps > 0)
                            )
                        )
                    if seasons_to_create:
                        Season.objects.bulk_create(seasons_to_create)
                imported += 1

        shows = list(Show.objects.filter(user=request.user).prefetch_related('seasons').all())
        stats = calculate_global_stats(shows, user=request.user)
        return JsonResponse({
            'success': True,
            'message': f'Successfully imported {imported} shows.',
            'shows': [s.to_dict() for s in shows],
            'stats': stats,
        })
    except Exception as e:
        logger.exception("Error in api_import_json: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def clean_html_tags(text):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    return clean.strip()


@require_http_methods(["GET"])
@require_user_auth
def api_search_external_shows(request):
    """Searches TVMaze and IMDb databases for series matching query with 0-buffering caching."""
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'success': True, 'results': []})

    cache_key = query.lower()
    cached = _get_from_cache(_EXTERNAL_SEARCH_CACHE, cache_key)
    if cached is not None:
        return JsonResponse({'success': True, 'results': cached, 'cached': True})

    try:
        url = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'ShowTrackerApp/2.0'})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            data = json.loads(response.read().decode('utf-8'))

        results = []
        for item in data[:8]:
            show = item.get('show', {})
            sid = show.get('id')
            if not sid or not show.get('name'):
                continue

            premiered = show.get('premiered') or ''
            year = int(premiered[:4]) if len(premiered) >= 4 and premiered[:4].isdigit() else None

            rating_obj = show.get('rating') or {}
            rating = rating_obj.get('average') or 0.0

            img_obj = show.get('image') or {}
            poster_url = img_obj.get('original') or img_obj.get('medium') or ''
            thumb_url = img_obj.get('medium') or poster_url

            platform = ''
            if show.get('webChannel'):
                platform = show['webChannel'].get('name', '')
            elif show.get('network'):
                platform = show['network'].get('name', '')

            genres_list = show.get('genres') or []
            genres_str = ", ".join(genres_list)
            summary = clean_html_tags(show.get('summary') or '')
            externals = show.get('externals') or {}
            imdb_id = externals.get('imdb') or ''

            results.append({
                'id': sid,
                'title': show.get('name'),
                'year': year,
                'rating': float(rating) if rating else 0.0,
                'poster_url': poster_url,
                'thumb_url': thumb_url,
                'platform': platform,
                'genres': genres_str,
                'summary': summary,
                'imdb_id': imdb_id,
                'status': 'COMPLETED' if show.get('status') == 'Ended' else 'WATCHING',
            })

        _set_in_cache(_EXTERNAL_SEARCH_CACHE, cache_key, results)
        return JsonResponse({'success': True, 'results': results, 'cached': False})
    except Exception as e:
        logger.exception("Error searching external shows for query '%s': %s", query, e)
        return JsonResponse({'success': False, 'error': str(e), 'results': []})


@require_http_methods(["GET"])
@require_user_auth
def api_fetch_external_show_details(request):
    """Fetches comprehensive metadata and exact per-season episode breakdown with caching."""
    show_id = request.GET.get('id', '').strip()
    if not show_id or not show_id.isdigit():
        return JsonResponse({'success': False, 'error': 'Invalid external show ID'}, status=400)

    cached = _get_from_cache(_EXTERNAL_DETAILS_CACHE, show_id)
    if cached is not None:
        return JsonResponse({'success': True, **cached, 'cached': True})

    try:
        url_show = f"https://api.tvmaze.com/shows/{show_id}"
        req_show = urllib.request.Request(url_show, headers={'User-Agent': 'ShowTrackerApp/2.0'})
        with urllib.request.urlopen(req_show, timeout=3.5) as resp_show:
            show = json.loads(resp_show.read().decode('utf-8'))

        url_episodes = f"https://api.tvmaze.com/shows/{show_id}/episodes"
        req_eps = urllib.request.Request(url_episodes, headers={'User-Agent': 'ShowTrackerApp/2.0'})
        with urllib.request.urlopen(req_eps, timeout=3.5) as resp_eps:
            episodes = json.loads(resp_eps.read().decode('utf-8'))

        season_counts = Counter(e.get('season') for e in episodes if e.get('season'))

        seasons_list = []
        if season_counts:
            for s_num in sorted(season_counts.keys()):
                seasons_list.append({
                    'season_number': s_num,
                    'total_episodes': max(1, season_counts[s_num]),
                    'episodes_watched': 0,
                })
        else:
            url_seasons = f"https://api.tvmaze.com/shows/{show_id}/seasons"
            req_seasons = urllib.request.Request(url_seasons, headers={'User-Agent': 'ShowTrackerApp/2.0'})
            with urllib.request.urlopen(req_seasons, timeout=3.5) as resp_seasons:
                seasons_data = json.loads(resp_seasons.read().decode('utf-8'))
            for s in seasons_data:
                s_num = s.get('number', 1)
                eps_order = s.get('episodeOrder') or 10
                seasons_list.append({
                    'season_number': s_num,
                    'total_episodes': max(1, eps_order),
                    'episodes_watched': 0,
                })

        if not seasons_list:
            seasons_list = [{'season_number': 1, 'total_episodes': 10, 'episodes_watched': 0}]

        premiered = show.get('premiered') or ''
        year = int(premiered[:4]) if len(premiered) >= 4 and premiered[:4].isdigit() else None

        rating_obj = show.get('rating') or {}
        rating = rating_obj.get('average') or 0.0

        img_obj = show.get('image') or {}
        poster_url = img_obj.get('original') or img_obj.get('medium') or ''

        platform = ''
        if show.get('webChannel'):
            platform = show['webChannel'].get('name', '')
        elif show.get('network'):
            platform = show['network'].get('name', '')

        genres_str = ", ".join(show.get('genres') or [])
        summary = clean_html_tags(show.get('summary') or '')
        status = 'COMPLETED' if show.get('status') == 'Ended' else 'WATCHING'

        result = {
            'title': show.get('name'),
            'release_year': year,
            'rating': float(rating) if rating else 0.0,
            'poster_url': poster_url,
            'platform': platform,
            'genres': genres_str,
            'notes': summary,
            'status': status,
            'total_seasons': len(seasons_list),
            'seasons': seasons_list,
        }

        _set_in_cache(_EXTERNAL_DETAILS_CACHE, show_id, result)
        return JsonResponse({'success': True, **result, 'cached': False})
    except Exception as e:
        logger.exception("Error fetching external show details for ID %s: %s", show_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@require_user_auth
def api_send_test_digest(request):
    """
    Sends a test monthly TV progress digest to the authenticated user's email address.
    """
    if not request.user.email or not request.user.email.strip():
        return JsonResponse({
            'success': False,
            'error': 'Your user profile does not have an email address associated with it. Please update your account email.'
        }, status=400)

    success, message = send_user_monthly_digest(request.user, force=True)
    if success:
        return JsonResponse({
            'success': True,
            'message': message,
            'email': request.user.email
        })
    else:
        return JsonResponse({
            'success': False,
            'error': message
        }, status=400)
