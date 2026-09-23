# SHOW TRACKER // Minimalist TV Series Matrix

A modern, high-contrast, black-and-white TV series and show tracker built with **Django 5.2**, **PostgreSQL**, and vanilla web technologies. It features a spreadsheet-style **season-by-season tabular matrix** where rows are shows and columns are seasons, interactive popover dropdowns for updating episode progress in real time, multi-user data isolation, Google OAuth 2.0 authentication, and automated monthly email digests.

---

## Key Features

### 1. Multi-User Authentication & Data Isolation
- **User Accounts**: Dedicated Sign In, Registration, and Session management with CSRF protection and `@username` session pills.
- **Google OAuth 2.0 / OpenID Connect**: Fast "Continue with Google" sign-in with automatic account creation and username collision handling.
- **Strict Data Isolation**: Each registered user maintains their own private show library, watch statistics, and custom season counts.
- **Per-User Uniqueness**: Different users can track identical show titles (e.g. both track "Severance") without title conflicts, while duplicate entries within a single user account are blocked.

### 2. Season-by-Season Tabular Matrix
- **Rows**: Tracked TV shows with poster thumbnails, title, release year, platform badge, rating, overall progress bar, quick $+1$ episode step pill, and action controls.
- **Columns**: Dynamic seasons ($S1, S2, S3 \dots S_N$) automatically expanding based on the highest season count among tracked shows.
- **Interactive Column Cells**:
  - Completed seasons display high-contrast filled pills with completion indicators (`10/10`).
  - In-progress seasons display outlined pills with progress indicators (`4/10`).
  - Empty seasons gracefully display muted placeholders (`—`).
  - **Custom Episode Popover Dropdown**: Click any season cell to open a popover featuring quick $+1 / -1$ episode steppers, a "Complete Season" toggle, and direct episode chips ($0 \dots N$) that update progress via AJAX instantly.

### 3. Automated Monthly Email Digests (Gmail SMTP)
- **Personalized Monthly Summary**: Dispatches responsive HTML and plain-text summaries of watching progress, active shows with next episode up indicators (e.g. `S02E05 Next`), completed highlights, and watchlist queue.
- **Management CLI Command**:
  ```bash
  # Simulate dispatch for all registered users (dry run)
  python3 manage.py send_monthly_updates --dry-run

  # Dispatch to all users via SMTP
  python3 manage.py send_monthly_updates

  # Dispatch to a single user
  python3 manage.py send_monthly_updates --user alex_rivera
  ```
- **Dashboard Trigger**: Authenticated users can test-send their own monthly digest preview from the header toolbar at any time.

### 4. External TV Database Integration & Auto-Fill
- **Live Search**: Instant autocomplete search against external TV databases by title with in-memory caching.
- **One-Click Metadata Auto-Fill**: Automatically fills title, poster image URL, release year, rating, network/platform, genres, synopsis, status, and custom season-by-season episode breakdowns.

### 5. Analytics Stats Dashboard
- Total Shows tracked (active vs completed vs watchlist vs dropped).
- Total Episodes Watched across all seasons.
- Overall Completion Rate percentage with progress bar.
- Estimated Hours watched (~45 min/ep avg).

### 6. Filters, Search & View Modes
- Live search by title, platform, genres, and notes (press `/` shortcut to focus).
- Filter tabs: *All*, *Watching*, *Plan to Watch*, *Completed*, *On Hold*, *Dropped*.
- Sorting: *Recently Updated*, *Title (A-Z)*, *Progress (High to Low)*, *Rating (High to Low)*, *Seasons (Most)*.
- View Mode Switcher: **Tabular Matrix View** vs **Cards Grid View**.

### 7. Reliability, Aesthetics & UX
- **Monochrome Design System**: Clean high-contrast palette with light and dark themes, 4px/8px spatial rhythm tokens, and typography pairing (Outfit, Plus Jakarta Sans, JetBrains Mono).
- **SpamGuard & Plain Loader**: Prevents rapid duplicate button clicks, API race conditions, and provides tactile button loading spinners and top progress indicators.
- **Toast Notifications**: Built-in notifications using Toastify.
- **Backup & Restore**: Export and import full JSON database backups scoped to the authenticated user.

---

## Project Structure

```
Show-Tracker/
├── manage.py                  # Django root management script
├── config/                    # Django project configuration
│   ├── settings.py            # Settings (apps, auth, SMTP, OAuth, db)
│   ├── urls.py                # Main URL router
│   ├── wsgi.py
│   └── asgi.py
├── tracker/                   # Show Tracker Application
│   ├── models.py              # User-scoped Show and Season models
│   ├── views.py               # Auth views, dashboard, and RESTful API endpoints
│   ├── urls.py                # URL endpoints (auth, api, oauth)
│   ├── email_service.py       # Digest compiler and SMTP multi-part sender
│   ├── admin.py               # Django Admin configuration
│   ├── tests.py               # 43 automated unit tests
│   ├── management/
│   │   └── commands/
│   │       └── send_monthly_updates.py # Monthly email dispatch CLI
│   └── migrations/            # Database schema migrations
├── templates/
│   ├── base.html              # Base shell with header, session pill, loader
│   ├── auth/
│   │   ├── login.html         # Sign In card with Google OAuth
│   │   └── register.html      # Account creation with Google OAuth
│   ├── emails/
│   │   ├── monthly_digest.html# Responsive monochrome email template
│   │   └── monthly_digest.txt # Plain-text email fallback
│   └── tracker/
│       └── index.html         # Main matrix dashboard, toolbar, modals
└── static/
    ├── css/
    │   └── tracker.css        # Zero-gradient monochrome CSS design system
    ├── js/
    │   └── tracker.js         # Reactive UI, SpamGuard, popovers & CRUD
    └── vendor/
        ├── toastify.css       # Toast notifications stylesheet
        └── toastify.js        # Toast notifications library
```

---

## Getting Started

### 1. Environment Configuration
Create a `.env` file from the provided template:
```bash
cp .env.example .env
```

Configure your environment variables:
```env
# Django Environment Configuration
SECRET_KEY=your-secure-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*

# Neon PostgreSQL Database Connection
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email / SMTP Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Show Tracker <your-email@gmail.com>
```

### 2. Apply Database Migrations
```bash
python3 manage.py migrate
```

### 3. Run Automated Tests
```bash
python3 manage.py test tracker
```

### 4. Start Development Server
```bash
python3 manage.py runserver 127.0.0.1:8080
```

### 5. Access the Application
Open `http://127.0.0.1:8080/` in your web browser.

---

## Google OAuth 2.0 Setup Guide

1. In [Google Cloud Console](https://console.cloud.google.com/), navigate to **APIs & Services > Credentials**.
2. Create an **OAuth 2.0 Client ID** (Web application).
3. Add the following **Authorized Redirect URI**:
   - `http://127.0.0.1:8080/oauth/google/callback/` (development)
   - `https://yourdomain.com/oauth/google/callback/` (production)
4. Copy the Client ID and Client Secret into your `.env` file.
