import math
from django.db import models
from django.db.models.functions import Lower
from django.contrib.auth.models import User


class Show(models.Model):
    STATUS_WATCHING = 'WATCHING'
    STATUS_PLAN_TO_WATCH = 'PLAN_TO_WATCH'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_ON_HOLD = 'ON_HOLD'
    STATUS_DROPPED = 'DROPPED'

    STATUS_CHOICES = [
        (STATUS_WATCHING, 'Watching'),
        (STATUS_PLAN_TO_WATCH, 'Plan to Watch'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_DROPPED, 'Dropped'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shows', db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    poster_url = models.URLField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WATCHING, db_index=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    total_seasons = models.PositiveIntegerField(default=1)
    release_year = models.PositiveIntegerField(blank=True, null=True)
    genres = models.CharField(max_length=255, blank=True, default='')
    platform = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at', 'title']
        indexes = [
            models.Index(fields=['user', 'status', '-updated_at']),
            models.Index(fields=['user', '-updated_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                'user',
                Lower('title'),
                name='unique_user_show_title_case_insensitive'
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.release_year or 'N/A'})"

    @property
    def total_episodes(self):
        # Optimized to use prefetched seasons without executing exists() queries
        return sum(s.total_episodes for s in self.seasons.all())

    @property
    def episodes_watched(self):
        # Optimized to use prefetched seasons without executing exists() queries
        return sum(s.episodes_watched for s in self.seasons.all())

    @property
    def progress_percentage(self):
        tot = self.total_episodes
        if tot == 0:
            return 0
        return min(100, int(round((self.episodes_watched / tot) * 100)))

    @property
    def is_all_completed(self):
        tot = self.total_episodes
        return tot > 0 and self.episodes_watched >= tot

    @property
    def current_progress_label(self):
        # Uses prefetched cache with in-memory sort
        seasons = sorted(self.seasons.all(), key=lambda s: s.season_number)
        if not seasons:
            return "No seasons"
        
        # Check if all completed
        if self.is_all_completed:
            return f"Completed ({len(seasons)}/{len(seasons)} Seasons)"
        
        # Find current in-progress season
        for s in seasons:
            if s.episodes_watched < s.total_episodes:
                return f"S{s.season_number} E{s.episodes_watched:02d} / {s.total_episodes:02d}"
        
        return "Completed"

    def sync_season_count(self, default_episodes=10):
        """Ensures the number of Season records matches self.total_seasons."""
        existing_seasons = sorted(self.seasons.all(), key=lambda s: s.season_number)
        current_count = len(existing_seasons)

        if current_count < self.total_seasons:
            new_seasons = []
            for s_num in range(current_count + 1, self.total_seasons + 1):
                new_seasons.append(
                    Season(
                        show=self,
                        season_number=s_num,
                        total_episodes=default_episodes,
                        episodes_watched=0
                    )
                )
            Season.objects.bulk_create(new_seasons)
        elif current_count > self.total_seasons:
            # Delete excess seasons from the end
            self.seasons.filter(season_number__gt=self.total_seasons).delete()

    def to_dict(self):
        # Optimized in-memory iteration without extra query
        seasons = [s.to_dict() for s in sorted(self.seasons.all(), key=lambda s: s.season_number)]
        return {
            'id': self.id,
            'title': self.title,
            'poster_url': self.poster_url or '',
            'status': self.status,
            'status_display': self.get_status_display(),
            'rating': float(self.rating),
            'total_seasons': self.total_seasons,
            'release_year': self.release_year,
            'genres': self.genres,
            'platform': self.platform,
            'notes': self.notes,
            'total_episodes': self.total_episodes,
            'episodes_watched': self.episodes_watched,
            'progress_percentage': self.progress_percentage,
            'current_progress_label': self.current_progress_label,
            'is_all_completed': self.is_all_completed,
            'seasons': seasons,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M'),
        }


class Season(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='seasons', db_index=True)
    season_number = models.PositiveIntegerField(default=1)
    total_episodes = models.PositiveIntegerField(default=10)
    episodes_watched = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['season_number']
        unique_together = ('show', 'season_number')
        indexes = [
            models.Index(fields=['show', 'season_number']),
        ]

    def __str__(self):
        return f"{self.show.title} - S{self.season_number} ({self.episodes_watched}/{self.total_episodes})"

    @property
    def progress_pct(self):
        if self.total_episodes == 0:
            return 0
        return min(100, int(round((self.episodes_watched / self.total_episodes) * 100)))

    def save(self, *args, **kwargs):
        # Validate clamping
        if self.total_episodes < 1:
            self.total_episodes = 1
        if self.episodes_watched > self.total_episodes:
            self.episodes_watched = self.total_episodes
        if self.episodes_watched < 0:
            self.episodes_watched = 0
        
        self.is_completed = (self.episodes_watched >= self.total_episodes and self.total_episodes > 0)
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'season_number': self.season_number,
            'total_episodes': self.total_episodes,
            'episodes_watched': self.episodes_watched,
            'is_completed': self.is_completed,
            'progress_pct': self.progress_pct,
        }
