from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/google/login/', views.google_oauth_login, name='google_login'),
    path('oauth/google/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path('api/shows/', views.api_get_shows, name='api_get_shows'),
    path('api/shows/create/', views.api_create_show, name='api_create_show'),
    path('api/shows/<int:show_id>/update/', views.api_update_show, name='api_update_show'),
    path('api/shows/<int:show_id>/delete/', views.api_delete_show, name='api_delete_show'),
    path('api/shows/<int:show_id>/quick-step/', views.api_quick_step, name='api_quick_step'),
    path('api/seasons/<int:season_id>/update-episode/', views.api_update_season_episode, name='api_update_season_episode'),
    path('api/seasons/<int:season_id>/toggle-complete/', views.api_toggle_season_complete, name='api_toggle_season_complete'),
    path('api/clear-all/', views.api_clear_all, name='api_clear_all'),
    path('api/export-json/', views.api_export_json, name='api_export_json'),
    path('api/import-json/', views.api_import_json, name='api_import_json'),
    path('api/search-external-shows/', views.api_search_external_shows, name='api_search_external_shows'),
    path('api/fetch-external-show-details/', views.api_fetch_external_show_details, name='api_fetch_external_show_details'),
    path('api/send-test-digest/', views.api_send_test_digest, name='api_send_test_digest'),
]
