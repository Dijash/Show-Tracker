# SHOW TRACKER // Minimalist TV Series Matrix

A modern, high-contrast, black-and-white TV series and show tracker built with **Django 5.2** and vanilla web technologies. It features a spreadsheet-style **season-by-season tabular matrix** where rows are shows and columns are seasons, with interactive popover dropdowns for updating episode progress in real time.

---

## Key Features

1. **Season-by-Season Tabular Matrix**:
   - **Rows**: Tracked TV shows with poster thumbnails, title, release year, platform badge, rating, overall progress bar, and action controls.
   - **Columns**: Dynamic seasons ($S1, S2, S3 \dots S_N$) automatically expanding based on the highest season count among tracked shows.
   - **Interactive Column Cells**:
     - Completed seasons display high-contrast filled pills with completion indicators (`10/10`).
     - In-progress seasons display outlined pills with progress indicators (`4/10`).
     - Empty seasons gracefully display muted placeholders (`—`).
     - **Custom Episode Popover Dropdown**: Click any season cell to open a popover featuring quick $+1 / -1$ episode steppers, a "Complete Season" toggle, and direct episode chips ($0 \dots N$) that update progress via AJAX instantly.

2. **Full CRUD Management**:
   - **Add Show**: Title, Poster URL, Release Year, Platform, Status (*Watching*, *Plan to Watch*, *Completed*, *On Hold*, *Dropped*), Rating ($0.0 - 10.0$), Genres, Notes, and a dynamic **Season & Episode Builder** allowing custom episode counts for each individual season.
   - **Edit Show**: Adjust all metadata and dynamically add, edit, or remove seasons.
   - **Delete Show**: Clean confirmation dialog.
   - **Show Detail Modal**: Full overview, synopsis/notes, rating, and season breakdown.

3. **Analytics Stats Dashboard**:
   - Total Shows tracked (active vs completed).
   - Total Episodes Watched across all seasons.
   - Overall Completion Rate percentage with progress bar.
   - Estimated Hours watched (~45 min/ep avg).

4. **Filters, Search & View Modes**:
   - Live search by title, platform, genres, and notes (press `/` shortcut to focus).
   - Filter tabs: *All*, *Watching*, *Plan to Watch*, *Completed*, *On Hold*, *Dropped*.
   - Sorting: *Recently Updated*, *Title (A-Z)*, *Progress (High to Low)*, *Rating (High to Low)*, *Seasons (Most)*.
   - View Mode Switcher: **Tabular Matrix View** vs **Cards Grid View**.

5. **Backup & Customization Tools**:
   - **Backup & Restore**: Export and Import JSON backups.
   - **Theme Switcher**: Dark Mode (default) & High-Contrast Light Mode.
   - **Keyboard Shortcuts**: `/` for search, `N` for new show, `Esc` to dismiss modals.

---

## Project Structure

```
Show-Tracker/
├── manage.py                  # Django root management script
├── config/                    # Django project configuration
│   ├── settings.py            # App settings (apps, templates, static)
│   ├── urls.py                # Main URL router
│   ├── wsgi.py
│   └── asgi.py
├── tracker/                   # Show Tracker Application
│   ├── models.py              # Show and Season database models
│   ├── views.py               # Index view and RESTful JSON API endpoints
│   ├── urls.py                # Tracker URL endpoints
│   ├── admin.py               # Django Admin configuration
│   ├── tests.py               # Automated unit test suite
│   └── migrations/            # Database schema migrations
├── templates/
│   ├── base.html              # Base shell with typography, theme & toasts
│   └── tracker/
│       └── index.html         # Main matrix dashboard, toolbar, modals
└── static/
    ├── css/
    │   └── tracker.css        # Zero-gradient monochrome CSS design system
    └── js/
        └── tracker.js         # Reactive UI, season popovers & CRUD
```

---

## Running the Application

### 1. Environment Setup
Create a `.env` file (or copy `.env.example`):
```bash
cp .env.example .env
```
Configure your secrets and Neon PostgreSQL connection:
```env
SECRET_KEY=your-secure-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*
DATABASE_URL=postgresql://neondb_owner:npg_uw40NMkbrQyz@ep-sparkling-moon-b58c0qgl-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### 2. Run Database Migrations & Tests
```bash
python3 manage.py migrate
python3 manage.py test
```

### 3. Start the Development Server
```bash
python3 manage.py runserver 127.0.0.1:8080
```

### 4. Open in Browser
Visit `http://127.0.0.1:8080/` in your web browser.
