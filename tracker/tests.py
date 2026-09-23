import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.core.management import call_command, CommandError
from django.contrib.auth.models import User
from tracker.models import Show, Season
from tracker.views import calculate_global_stats
from tracker.email_service import generate_user_digest_data, send_user_monthly_digest, send_all_monthly_digests


class ShowTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        self.client.force_login(self.user)

        self.show = Show.objects.create(
            user=self.user,
            title="Severance",
            status=Show.STATUS_WATCHING,
            rating=9.4,
            release_year=2022,
            genres="Sci-Fi, Mystery",
            platform="Apple TV+",
            notes="Lumon Industries mystery",
            total_seasons=2
        )
        self.season1 = Season.objects.create(
            show=self.show,
            season_number=1,
            total_episodes=9,
            episodes_watched=9
        )
        self.season2 = Season.objects.create(
            show=self.show,
            season_number=2,
            total_episodes=10,
            episodes_watched=4
        )

    # -------------------------------------------------------------------------
    # Authentication & Session Tests
    # -------------------------------------------------------------------------
    def test_unauthenticated_user_redirected_to_login(self):
        unauthed_client = Client()
        response = unauthed_client.get(reverse('tracker:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_unauthenticated_api_request_blocked(self):
        unauthed_client = Client()
        response = unauthed_client.get(reverse('tracker:api_get_shows'))
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn("authentication required", data['error'].lower())

    def test_user_registration_success(self):
        anon_client = Client()
        response = anon_client.post(reverse('tracker:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepassword',
            'password_confirm': 'securepassword',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tracker:index'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_registration_password_mismatch(self):
        anon_client = Client()
        response = anon_client.post(reverse('tracker:register'), {
            'username': 'mismatchuser',
            'email': '',
            'password': 'password123',
            'password_confirm': 'password999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match")
        self.assertFalse(User.objects.filter(username='mismatchuser').exists())

    def test_user_registration_existing_username(self):
        anon_client = Client()
        response = anon_client.post(reverse('tracker:register'), {
            'username': 'testuser',  # already taken in setUp
            'email': '',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already taken")

    def test_user_login_success_and_logout(self):
        anon_client = Client()
        # Login
        response = anon_client.post(reverse('tracker:login'), {
            'username': 'testuser',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tracker:index'))

        # Logout
        logout_resp = anon_client.get(reverse('tracker:logout'))
        self.assertEqual(logout_resp.status_code, 302)
        self.assertEqual(logout_resp.url, reverse('tracker:login'))

    def test_user_login_invalid_credentials(self):
        anon_client = Client()
        response = anon_client.post(reverse('tracker:login'), {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    # -------------------------------------------------------------------------
    # Multi-User Data Isolation Tests
    # -------------------------------------------------------------------------
    def test_multi_user_show_isolation(self):
        # Create second user
        other_user = User.objects.create_user(username="otheruser", password="password123")
        other_client = Client()
        other_client.force_login(other_user)

        # Other user's dashboard should be empty initially
        get_resp = other_client.get(reverse('tracker:api_get_shows'))
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(len(get_resp.json()['shows']), 0)

        # Other user cannot update testuser's show (returns 404)
        upd_resp = other_client.post(
            reverse('tracker:api_update_show', args=[self.show.id]),
            data=json.dumps({"title": "Hacked Title"}),
            content_type="application/json"
        )
        self.assertEqual(upd_resp.status_code, 404)

        # Other user cannot step testuser's show (returns 404)
        step_resp = other_client.post(
            reverse('tracker:api_quick_step', args=[self.show.id]),
            data=json.dumps({"direction": 1}),
            content_type="application/json"
        )
        self.assertEqual(step_resp.status_code, 404)

        # Other user cannot delete testuser's show (returns 404)
        del_resp = other_client.post(reverse('tracker:api_delete_show', args=[self.show.id]))
        self.assertEqual(del_resp.status_code, 404)
        self.assertTrue(Show.objects.filter(id=self.show.id).exists())

    def test_same_show_title_across_different_users_allowed(self):
        # User 1 has "Severance"
        # User 2 should also be able to create "Severance"
        user2 = User.objects.create_user(username="user2", password="password123")
        client2 = Client()
        client2.force_login(user2)

        payload = {
            "title": "Severance",
            "status": "PLAN_TO_WATCH",
            "total_seasons": 1,
            "seasons": [{"season_number": 1, "total_episodes": 9, "episodes_watched": 0}]
        }
        resp = client2.post(
            reverse('tracker:api_create_show'),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])

        # Both shows should exist in database with different user owners
        self.assertEqual(Show.objects.filter(title__iexact="Severance").count(), 2)

    def test_same_user_duplicate_show_rejected(self):
        # testuser already has "Severance"
        payload = {
            "title": "severance",  # case-insensitive duplicate
            "status": "WATCHING",
            "total_seasons": 1,
            "seasons": [{"season_number": 1, "total_episodes": 10, "episodes_watched": 0}]
        }
        response = self.client.post(
            reverse('tracker:api_create_show'),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn("already exists", data['error'].lower())

    # -------------------------------------------------------------------------
    # Core Show Model & CRUD Tests
    # -------------------------------------------------------------------------
    def test_show_properties_and_calculations(self):
        self.assertEqual(self.show.total_episodes, 19)
        self.assertEqual(self.show.episodes_watched, 13)
        self.assertEqual(self.show.progress_percentage, 68)
        self.assertFalse(self.show.is_all_completed)
        self.assertEqual(self.show.current_progress_label, "S2 E04 / 10")
        self.assertTrue(self.season1.is_completed)
        self.assertFalse(self.season2.is_completed)

    def test_index_view_renders(self):
        response = self.client.get(reverse('tracker:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SHOW")
        self.assertContains(response, "Severance")
        self.assertContains(response, "@testuser")

    def test_api_create_show(self):
        payload = {
            "title": "The Bear",
            "status": "WATCHING",
            "rating": 9.2,
            "release_year": 2022,
            "genres": "Drama, Comedy",
            "platform": "Hulu",
            "notes": "Yes Chef",
            "seasons": [
                {"season_number": 1, "total_episodes": 8, "episodes_watched": 8},
                {"season_number": 2, "total_episodes": 10, "episodes_watched": 5},
            ]
        }
        response = self.client.post(
            reverse('tracker:api_create_show'),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['show']['title'], "The Bear")
        self.assertEqual(len(data['show']['seasons']), 2)

    def test_api_update_show(self):
        payload = {
            "title": "Severance (Updated)",
            "status": "COMPLETED",
            "rating": 9.8,
            "seasons": [
                {"season_number": 1, "total_episodes": 9, "episodes_watched": 9},
                {"season_number": 2, "total_episodes": 10, "episodes_watched": 10},
                {"season_number": 3, "total_episodes": 10, "episodes_watched": 0},
            ]
        }
        response = self.client.post(
            reverse('tracker:api_update_show', args=[self.show.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['show']['title'], "Severance (Updated)")
        self.assertEqual(len(data['show']['seasons']), 3)

    def test_api_update_season_episode(self):
        payload = {"episodes_watched": 10}
        response = self.client.post(
            reverse('tracker:api_update_season_episode', args=[self.season2.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['season']['episodes_watched'], 10)
        self.assertTrue(data['season']['is_completed'])
        self.assertEqual(data['show']['progress_percentage'], 100)
        self.assertEqual(data['show']['status'], Show.STATUS_COMPLETED)

    def test_api_toggle_season_complete(self):
        response = self.client.post(
            reverse('tracker:api_toggle_season_complete', args=[self.season2.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['season']['episodes_watched'], 10)
        self.assertTrue(data['season']['is_completed'])

        # Toggle again -> should reset to 0/10
        response2 = self.client.post(
            reverse('tracker:api_toggle_season_complete', args=[self.season2.id])
        )
        data2 = response2.json()
        self.assertEqual(data2['season']['episodes_watched'], 0)
        self.assertFalse(data2['season']['is_completed'])

    def test_api_quick_step(self):
        response = self.client.post(
            reverse('tracker:api_quick_step', args=[self.show.id]),
            data=json.dumps({"direction": 1}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['show']['episodes_watched'], 14)

    def test_api_delete_show(self):
        show_id = self.show.id
        response = self.client.post(
            reverse('tracker:api_delete_show', args=[show_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Show.objects.filter(id=show_id).exists())

    def test_api_clear_all(self):
        response = self.client.post(reverse('tracker:api_clear_all'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Show.objects.filter(user=self.user).count(), 0)

    def test_export_and_import(self):
        export_resp = self.client.get(reverse('tracker:api_export_json'))
        self.assertEqual(export_resp.status_code, 200)
        backup_data = json.loads(export_resp.content.decode('utf-8'))
        self.assertIn('shows', backup_data)
        self.assertEqual(backup_data.get('username'), 'testuser')

        Show.objects.filter(user=self.user).delete()
        self.assertEqual(Show.objects.filter(user=self.user).count(), 0)

        import_resp = self.client.post(
            reverse('tracker:api_import_json'),
            data=json.dumps(backup_data),
            content_type="application/json"
        )
        self.assertEqual(import_resp.status_code, 200)
        self.assertGreater(Show.objects.filter(user=self.user).count(), 0)

    # -------------------------------------------------------------------------
    # External TV Database Integration Tests
    # -------------------------------------------------------------------------
    def test_api_search_external_shows(self):
        response = self.client.get(reverse('tracker:api_search_external_shows'), {'q': 'breaking bad'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['results']), 0)
        self.assertEqual(data['results'][0]['title'], "Breaking Bad")

        # Repeat query should return cached: True with zero network overhead
        response2 = self.client.get(reverse('tracker:api_search_external_shows'), {'q': 'breaking bad'})
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertTrue(data2.get('cached', False))

    def test_api_fetch_external_show_details(self):
        response = self.client.get(reverse('tracker:api_fetch_external_show_details'), {'id': '169'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], "Breaking Bad")
        self.assertEqual(data['total_seasons'], 5)
        self.assertEqual(len(data['seasons']), 5)

        # Repeat query should return cached: True
        response2 = self.client.get(reverse('tracker:api_fetch_external_show_details'), {'id': '169'})
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertTrue(data2.get('cached', False))

    def test_query_count_on_index_and_stats(self):
        shows = list(Show.objects.filter(user=self.user).prefetch_related('seasons').all())
        with self.assertNumQueries(0):
            stats = calculate_global_stats(shows, user=self.user)
            self.assertEqual(stats['total_shows'], 1)

    # -------------------------------------------------------------------------
    # Google OAuth 2.0 Integration Tests
    # -------------------------------------------------------------------------
    def test_google_oauth_login_initiates_redirect(self):
        anon_client = Client()
        response = anon_client.get(reverse('tracker:google_login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('https://accounts.google.com/o/oauth2/v2/auth'))
        self.assertIn('client_id=', response.url)
        self.assertIn('scope=openid+email+profile', response.url)
        self.assertIn('state=', response.url)
        # Verify state is saved in session
        self.assertIn('oauth_google_state', anon_client.session)

    def test_google_oauth_login_preserves_next_param(self):
        anon_client = Client()
        response = anon_client.get(reverse('tracker:google_login') + '?next=/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(anon_client.session.get('oauth_google_next'), '/')

    @patch('requests.get')
    @patch('requests.post')
    def test_google_oauth_callback_creates_and_logs_in_new_user(self, mock_post, mock_get):
        anon_client = Client()
        # Initialize session state
        session = anon_client.session
        session['oauth_google_state'] = 'test_state_12345'
        session.save()

        # Mock token response
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {
            'access_token': 'mock_google_access_token',
            'id_token': 'mock_id_token',
        }
        mock_post.return_value = mock_token_resp

        # Mock userinfo response
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {
            'email': 'maya.lin@example.com',
            'name': 'Maya Lin',
            'given_name': 'Maya',
            'family_name': 'Lin',
            'sub': 'google_123456789',
        }
        mock_get.return_value = mock_userinfo_resp

        response = anon_client.get(reverse('tracker:google_oauth_callback'), {
            'code': 'mock_auth_code',
            'state': 'test_state_12345',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tracker:index'))

        # Check that new user was created
        created_user = User.objects.filter(email='maya.lin@example.com').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.username, 'maya.lin')
        self.assertFalse(created_user.has_usable_password())

    @patch('requests.get')
    @patch('requests.post')
    def test_google_oauth_callback_authenticates_existing_user(self, mock_post, mock_get):
        anon_client = Client()
        session = anon_client.session
        session['oauth_google_state'] = 'state_existing_user'
        session.save()

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {'access_token': 'mock_token'}
        mock_post.return_value = mock_token_resp

        # Existing user has email test@example.com (from setUp)
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {
            'email': 'test@example.com',
            'name': 'Test User',
            'given_name': 'Test',
            'family_name': 'User',
            'sub': 'google_999999',
        }
        mock_get.return_value = mock_userinfo_resp

        response = anon_client.get(reverse('tracker:google_oauth_callback'), {
            'code': 'mock_auth_code',
            'state': 'state_existing_user',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tracker:index'))
        # Should not create duplicate user
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 1)

    def test_google_oauth_callback_state_mismatch_rejected(self):
        anon_client = Client()
        session = anon_client.session
        session['oauth_google_state'] = 'correct_state'
        session.save()

        response = anon_client.get(reverse('tracker:google_oauth_callback'), {
            'code': 'mock_auth_code',
            'state': 'tampered_state',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid OAuth session state")

    def test_google_oauth_callback_handles_google_error(self):
        anon_client = Client()
        session = anon_client.session
        session['oauth_google_state'] = 'some_state'
        session.save()

        response = anon_client.get(reverse('tracker:google_oauth_callback'), {
            'error': 'access_denied',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cancelled or failed")

    @patch('requests.post')
    def test_google_oauth_callback_token_exchange_failure(self, mock_post):
        anon_client = Client()
        session = anon_client.session
        session['oauth_google_state'] = 'token_fail_state'
        session.save()

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 400
        mock_token_resp.text = '{"error": "invalid_grant"}'
        mock_post.return_value = mock_token_resp

        response = anon_client.get(reverse('tracker:google_oauth_callback'), {
            'code': 'invalid_code',
            'state': 'token_fail_state',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed to exchange authorization code")

    @patch('requests.get')
    @patch('requests.post')
    def test_google_oauth_callback_resolves_username_collision(self, mock_post, mock_get):
        # User 'testuser' already exists with email 'test@example.com'
        anon_client = Client()
        session = anon_client.session
        session['oauth_google_state'] = 'collision_state'
        session.save()

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {'access_token': 'mock_token'}
        mock_post.return_value = mock_token_resp

        # New user has email testuser@otherdomain.com -> base username 'testuser' is taken
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {
            'email': 'testuser@otherdomain.com',
            'name': 'Other Test User',
            'given_name': 'Other',
            'family_name': 'User',
            'sub': 'google_88888',
        }
        mock_get.return_value = mock_userinfo_resp

        response = anon_client.get(reverse('tracker:google_oauth_callback'), {
            'code': 'mock_code',
            'state': 'collision_state',
        })

        self.assertEqual(response.status_code, 302)
        resolved_user = User.objects.filter(email='testuser@otherdomain.com').first()
        self.assertIsNotNone(resolved_user)
        self.assertEqual(resolved_user.username, 'testuser_1')

    # -------------------------------------------------------------------------
    # Monthly Email Digest Service & Command Tests
    # -------------------------------------------------------------------------
    def test_generate_user_digest_data(self):
        data = generate_user_digest_data(self.user)
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['total_shows'], 1)
        self.assertEqual(data['watching_count'], 1)
        self.assertEqual(data['total_episodes_watched'], 13)
        self.assertEqual(data['total_episodes_available'], 19)
        self.assertGreaterEqual(data['overall_completion_pct'], 68)
        self.assertEqual(len(data['watching_shows']), 1)
        # Check active season info
        show_info = data['watching_shows'][0]
        self.assertIsNotNone(show_info['current_season_info'])
        self.assertEqual(show_info['current_season_info']['season_number'], 2)
        self.assertEqual(show_info['current_season_info']['next_episode'], 5)

    def test_send_user_monthly_digest_success(self):
        mail.outbox = []
        success, msg = send_user_monthly_digest(self.user)
        self.assertTrue(success)
        self.assertIn("Monthly digest sent to test@example.com", msg)
        self.assertEqual(len(mail.outbox), 1)

        sent_mail = mail.outbox[0]
        self.assertIn("Monthly TV Progress Digest", sent_mail.subject)
        self.assertEqual(sent_mail.to, ['test@example.com'])
        self.assertIn("Severance", sent_mail.body)
        self.assertEqual(len(sent_mail.alternatives), 1)
        html_body, mime_type = sent_mail.alternatives[0]
        self.assertEqual(mime_type, "text/html")
        self.assertIn("Severance", html_body)
        self.assertIn("SHOW TRACKER", html_body)

    def test_send_user_monthly_digest_dry_run(self):
        mail.outbox = []
        success, msg = send_user_monthly_digest(self.user, dry_run=True)
        self.assertTrue(success)
        self.assertIn("[DRY-RUN]", msg)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_user_monthly_digest_no_email_skipped(self):
        no_email_user = User.objects.create_user(username="no_email_user", email="", password="password123")
        mail.outbox = []
        success, msg = send_user_monthly_digest(no_email_user)
        self.assertFalse(success)
        self.assertIn("does not have an email address", msg)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_user_monthly_digest_zero_shows_skipped_without_force(self):
        zero_shows_user = User.objects.create_user(username="empty_user", email="empty@example.com", password="password123")
        mail.outbox = []
        success, msg = send_user_monthly_digest(zero_shows_user, force=False)
        self.assertFalse(success)
        self.assertIn("0 shows tracked", msg)
        self.assertEqual(len(mail.outbox), 0)

        # With force=True, it sends
        success, msg = send_user_monthly_digest(zero_shows_user, force=True)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_all_monthly_digests(self):
        mail.outbox = []
        # User 'testuser' has 1 show
        results = send_all_monthly_digests()
        self.assertGreaterEqual(results['sent'], 1)
        self.assertEqual(results['failed'], 0)
        self.assertGreaterEqual(len(mail.outbox), 1)

    def test_send_monthly_updates_command_single_user(self):
        mail.outbox = []
        call_command('send_monthly_updates', user='testuser', dry_run=True)
        self.assertEqual(len(mail.outbox), 0)  # dry run

        call_command('send_monthly_updates', user='testuser')
        self.assertEqual(len(mail.outbox), 1)

    def test_send_monthly_updates_command_all_users_dry_run(self):
        mail.outbox = []
        call_command('send_monthly_updates', dry_run=True)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_monthly_updates_command_invalid_user_raises_error(self):
        with self.assertRaises(CommandError):
            call_command('send_monthly_updates', user='nonexistent_user_xyz')

    def test_api_send_test_digest_authenticated_success(self):
        mail.outbox = []
        response = self.client.post(reverse('tracker:api_send_test_digest'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(len(mail.outbox), 1)

    def test_api_send_test_digest_unauthenticated_blocked(self):
        unauthed_client = Client()
        response = unauthed_client.post(reverse('tracker:api_send_test_digest'))
        self.assertEqual(response.status_code, 401)

    def test_api_send_test_digest_user_without_email_fails(self):
        no_email_user = User.objects.create_user(username="no_email_guy", email="", password="password123")
        custom_client = Client()
        custom_client.force_login(no_email_user)
        response = custom_client.post(reverse('tracker:api_send_test_digest'))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn("does not have an email", data['error'])
