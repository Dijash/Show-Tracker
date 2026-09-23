from django.contrib import admin
from .models import Show, Season


class SeasonInline(admin.TabularInline):
    model = Season
    extra = 0
    fields = ('season_number', 'total_episodes', 'episodes_watched', 'is_completed')


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'rating', 'total_seasons', 'episodes_watched', 'total_episodes', 'progress_percentage', 'updated_at')
    list_filter = ('status', 'platform')
    search_fields = ('title', 'genres', 'notes')
    inlines = [SeasonInline]


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('show', 'season_number', 'episodes_watched', 'total_episodes', 'is_completed')
    list_filter = ('is_completed', 'show')
    search_fields = ('show__title',)
