/**
 * SHOW TRACKER // Minimalist Series Matrix Frontend Engine
 * Modern Vanilla JS with Optimistic UI, Micro-Interactions, Client Caching & Reactive State
 */

(function () {
    'use strict';

    // Application State
    const AppState = {
        shows: [],
        currentFilter: 'ALL',
        currentSearch: '',
        currentSort: 'updated_desc',
        viewMode: 'matrix', // 'matrix' or 'cards'
        activePopover: null,
        editingShowId: null,
        deletingShowId: null,
    };

    // Client-side Memory Caches to eliminate buffering
    const searchCache = new Map();
    const detailsCache = new Map();

    // DOM Elements
    const elements = {
        matrixViewContainer: document.getElementById('matrix-view-container'),
        cardsViewContainer: document.getElementById('cards-view-container'),
        matrixTableBody: document.getElementById('matrix-table-body'),
        seasonHeadersList: document.getElementById('season-headers-list'),
        seasonHeadersWrap: document.getElementById('season-headers-wrap'),
        emptyState: document.getElementById('empty-state'),
        searchInput: document.getElementById('search-input'),
        searchClearBtn: document.getElementById('search-clear-btn'),
        sortSelect: document.getElementById('sort-select'),
        filterTabs: document.querySelectorAll('.tab-btn'),
        btnViewMatrix: document.getElementById('btn-view-matrix'),
        btnViewCards: document.getElementById('btn-view-cards'),
        themeToggle: document.getElementById('theme-toggle'),
        toastContainer: document.getElementById('toast-container'),

        // Stats
        statTotalShows: document.getElementById('stat-total-shows'),
        statWatchingCount: document.getElementById('stat-watching-count'),
        statCompletedCount: document.getElementById('stat-completed-count'),
        statEpisodesWatched: document.getElementById('stat-episodes-watched'),
        statTotalEpisodes: document.getElementById('stat-total-episodes'),
        statCompletionPct: document.getElementById('stat-completion-pct'),
        statProgressBar: document.getElementById('stat-progress-bar'),
        statHours: document.getElementById('stat-hours'),

        // Tab counts
        countAll: document.getElementById('count-all'),
        countWatching: document.getElementById('count-watching'),
        countPlan: document.getElementById('count-plan'),
        countCompleted: document.getElementById('count-completed'),
        countHold: document.getElementById('count-hold'),
        countDropped: document.getElementById('count-dropped'),

        // Modals
        showFormModal: document.getElementById('show-form-modal'),
        showForm: document.getElementById('show-form'),
        formModalTitle: document.getElementById('form-modal-title'),
        btnOpenAddModal: document.getElementById('btn-open-add-modal'),
        btnCloseFormModal: document.getElementById('btn-close-form-modal'),
        btnCancelForm: document.getElementById('btn-cancel-form'),
        btnAddSeasonRow: document.getElementById('btn-add-season-row'),
        seasonsRowsContainer: document.getElementById('seasons-rows-container'),

        // Form Fields & Autocomplete
        formShowId: document.getElementById('form-show-id'),
        formTitle: document.getElementById('form-title'),
        autocompleteDropdown: document.getElementById('title-autocomplete-dropdown'),
        autocompleteSpinner: document.getElementById('autocomplete-spinner'),
        formYear: document.getElementById('form-year'),
        formPoster: document.getElementById('form-poster'),
        formPosterPreview: document.getElementById('form-poster-preview'),
        formPosterImg: document.getElementById('form-poster-img'),
        formPlatform: document.getElementById('form-platform'),
        formStatus: document.getElementById('form-status'),
        formRating: document.getElementById('form-rating'),
        formGenres: document.getElementById('form-genres'),
        formNotes: document.getElementById('form-notes'),

        // Detail Modal
        showDetailModal: document.getElementById('show-detail-modal'),
        detailModalTitle: document.getElementById('detail-modal-title'),
        detailSubMeta: document.getElementById('detail-sub-meta'),
        detailPosterBox: document.getElementById('detail-poster-box'),
        detailRating: document.getElementById('detail-rating'),
        detailProgress: document.getElementById('detail-progress'),
        detailStatus: document.getElementById('detail-status'),
        detailGenres: document.getElementById('detail-genres'),
        detailNotes: document.getElementById('detail-notes'),
        detailSeasonsList: document.getElementById('detail-seasons-list'),
        btnCloseDetailModal: document.getElementById('btn-close-detail-modal'),
        btnDetailClose: document.getElementById('btn-detail-close'),
        btnDetailEdit: document.getElementById('btn-detail-edit'),

        // Delete Modal
        deleteConfirmModal: document.getElementById('delete-confirm-modal'),
        deleteShowTitle: document.getElementById('delete-show-title'),
        btnCloseDeleteModal: document.getElementById('btn-close-delete-modal'),
        btnCancelDelete: document.getElementById('btn-cancel-delete'),
        btnConfirmDelete: document.getElementById('btn-confirm-delete'),

        // Popover
        seasonPopover: document.getElementById('season-popover'),
        popoverSeasonTitle: document.getElementById('popover-season-title'),
        popoverSeasonSub: document.getElementById('popover-season-sub'),
        popoverCloseBtn: document.getElementById('popover-close-btn'),
        popoverBtnStepDown: document.getElementById('popover-btn-step-down'),
        popoverBtnStepUp: document.getElementById('popover-btn-step-up'),
        popoverBtnToggleAll: document.getElementById('popover-btn-toggle-all'),
        popoverToggleText: document.getElementById('popover-toggle-text'),
        popoverEpisodesGrid: document.getElementById('popover-episodes-grid'),

        // Backup & Restore
        btnEmptyAdd: document.getElementById('btn-empty-add'),
        btnExportJson: document.getElementById('btn-export-json'),
        btnImportTrigger: document.getElementById('btn-import-trigger'),
        importFileInput: document.getElementById('import-file-input'),
        btnSaveShow: document.getElementById('btn-save-show'),
        btnConfirmDelete: document.getElementById('btn-confirm-delete'),
        globalLoaderBar: document.getElementById('global-loader-bar'),
    };

    // Helper: CSRF Token
    function getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        if (cookieValue) return cookieValue;
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    // =========================================================================
    // GLOBAL PLAIN MINIMALIST LOADING CONTROLLER
    // =========================================================================
    const Loading = {
        activeRequests: 0,
        barEl: null,
        progressEl: null,

        getElements() {
            if (!this.barEl) {
                this.barEl = document.getElementById('global-loader-bar');
            }
            if (this.barEl && !this.progressEl) {
                this.progressEl = this.barEl.querySelector('.global-loader-progress');
            }
        },

        start() {
            this.activeRequests++;
            this.getElements();
            if (this.barEl) {
                this.barEl.style.display = 'block';
                if (this.progressEl) {
                    this.progressEl.classList.add('indeterminate');
                    this.progressEl.style.opacity = '1';
                }
            }
        },

        done() {
            this.activeRequests = Math.max(0, this.activeRequests - 1);
            if (this.activeRequests === 0) {
                this.getElements();
                if (this.progressEl) {
                    this.progressEl.classList.remove('indeterminate');
                    this.progressEl.style.width = '100%';
                    setTimeout(() => {
                        this.progressEl.style.opacity = '0';
                        setTimeout(() => {
                            if (this.activeRequests === 0 && this.barEl) {
                                this.barEl.style.display = 'none';
                                this.progressEl.style.width = '0%';
                            }
                        }, 200);
                    }, 150);
                } else if (this.barEl) {
                    this.barEl.style.display = 'none';
                }
            }
        },

        setButtonLoading(btn, isLoading, loadingText = '') {
            if (!btn) return;
            if (isLoading) {
                btn.classList.add('is-loading');
                btn.disabled = true;
                btn.dataset.originalHtml = btn.innerHTML;
                btn.innerHTML = `<span class="plain-spinner" aria-hidden="true"></span> <span>${escapeHtml(loadingText || 'Loading...')}</span>`;
            } else {
                btn.classList.remove('is-loading');
                btn.disabled = false;
                if (btn.dataset.originalHtml) {
                    btn.innerHTML = btn.dataset.originalHtml;
                    delete btn.dataset.originalHtml;
                }
            }
        }
    };

    // =========================================================================
    // SPAM PROTECTION & ACTION LOCK SYSTEM
    // =========================================================================
    const SpamGuard = {
        locks: new Map(),

        /**
         * Try to acquire a lock for an action key.
         * Returns true if lock was acquired, false if spammed/locked.
         */
        acquire(key, cooldownMs = 300) {
            const now = Date.now();
            if (this.locks.has(key)) {
                const expiresAt = this.locks.get(key);
                if (now < expiresAt) {
                    return false; // Spam blocked
                }
            }
            this.locks.set(key, now + cooldownMs);
            return true;
        },

        release(key) {
            this.locks.delete(key);
        },

        guardClick(btn, cooldownMs = 350) {
            if (!btn) return false;
            if (btn.disabled || btn.classList.contains('is-locked') || btn.classList.contains('is-loading')) {
                return false;
            }
            btn.classList.add('is-locked');
            setTimeout(() => {
                btn.classList.remove('is-locked');
            }, cooldownMs);
            return true;
        }
    };

    // =========================================================================
    // TOAST NOTIFICATION ENGINE (POWERED BY TOASTIFY JS)
    // =========================================================================
    const Toast = {
        show(message, type = 'info', options = {}) {
            const iconMap = {
                success: '<svg class="toast-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
                error: '<svg class="toast-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
                warning: '<svg class="toast-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
                info: '<svg class="toast-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
            };

            const iconSvg = iconMap[type] || iconMap.info;
            const contentHtml = `
                <div class="toastify-body">
                    <div class="toastify-icon-box toastify-icon-${type}">${iconSvg}</div>
                    <div class="toastify-message">${escapeHtml(message)}</div>
                </div>
            `;

            if (typeof Toastify === 'function') {
                Toastify({
                    text: contentHtml,
                    escapeMarkup: false,
                    duration: options.duration || (type === 'error' ? 4500 : 3200),
                    close: true,
                    gravity: 'top',
                    position: 'right',
                    stopOnFocus: true,
                    className: `toastify-tracker toastify-${type}`,
                    offset: {
                        x: 16,
                        y: 16
                    },
                    onClick: options.onClick || function() {}
                }).showToast();
            } else {
                // Graceful DOM fallback
                const toast = document.createElement('div');
                toast.className = `toast-item toast-${type}`;
                toast.innerHTML = `${iconSvg} <span>${escapeHtml(message)}</span>`;
                if (elements.toastContainer) {
                    elements.toastContainer.appendChild(toast);
                    setTimeout(() => {
                        toast.classList.add('leaving');
                        setTimeout(() => toast.remove(), 200);
                    }, 3200);
                }
            }
        },
        success(msg, opts) { this.show(msg, 'success', opts); },
        error(msg, opts) { this.show(msg, 'error', opts); },
        warning(msg, opts) { this.show(msg, 'warning', opts); },
        info(msg, opts) { this.show(msg, 'info', opts); }
    };

    function showToast(message, type = 'info', options = {}) {
        Toast.show(message, type, options);
    }

    // Helper: HTML Escaper
    function escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Theme Management
    function initTheme() {
        const savedTheme = localStorage.getItem('show_tracker_theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        if (elements.themeToggle) {
            elements.themeToggle.addEventListener('click', () => {
                if (!SpamGuard.acquire('theme_toggle', 250)) return;
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('show_tracker_theme', next);
                showToast(`Switched to ${next} theme`, 'info');
            });
        }
    }

    // Initial Data Loader
    function initData() {
        const initialScript = document.getElementById('initial-shows-data');
        if (initialScript && initialScript.textContent) {
            try {
                AppState.shows = JSON.parse(initialScript.textContent);
            } catch (e) {
                console.error('Failed to parse initial shows data:', e);
                AppState.shows = [];
            }
        }
    }

    // Recalculate single show metrics optimistically in memory
    function recalculateShowProgress(show) {
        if (!show || !show.seasons) return;
        let totEps = 0;
        let watchedEps = 0;
        let inProgressLabel = 'No seasons';
        let allCompleted = true;

        show.seasons.sort((a, b) => (a.season_number || 0) - (b.season_number || 0));

        for (const s of show.seasons) {
            s.total_episodes = Math.max(1, parseInt(s.total_episodes, 10) || 1);
            s.episodes_watched = Math.max(0, Math.min(s.total_episodes, parseInt(s.episodes_watched, 10) || 0));
            s.is_completed = (s.episodes_watched >= s.total_episodes && s.total_episodes > 0);
            s.progress_pct = Math.min(100, Math.round((s.episodes_watched / s.total_episodes) * 100));

            totEps += s.total_episodes;
            watchedEps += s.episodes_watched;

            if (!s.is_completed) {
                allCompleted = false;
                if (inProgressLabel === 'No seasons') {
                    inProgressLabel = `S${s.season_number} E${String(s.episodes_watched).padStart(2, '0')} / ${s.total_episodes}`;
                }
            }
        }

        show.total_episodes = totEps;
        show.episodes_watched = watchedEps;
        show.progress_percentage = totEps > 0 ? Math.min(100, Math.round((watchedEps / totEps) * 100)) : 0;
        show.is_all_completed = (totEps > 0 && watchedEps >= totEps);

        if (show.is_all_completed) {
            show.status = 'COMPLETED';
            show.current_progress_label = `Completed (${show.seasons.length}/${show.seasons.length} Seasons)`;
        } else {
            show.current_progress_label = inProgressLabel !== 'No seasons' ? inProgressLabel : 'Completed';
            if (show.status === 'COMPLETED') {
                show.status = 'WATCHING';
            } else if (show.status === 'PLAN_TO_WATCH' && watchedEps > 0) {
                show.status = 'WATCHING';
            }
        }
        show.status_display = formatStatus(show.status);
    }

    // Stats Calculator & UI Updater
    function updateStatsUI(stats) {
        if (!stats) {
            let totalEpisodes = 0;
            let episodesWatched = 0;
            let watching = 0;
            let completed = 0;
            let plan = 0;
            let hold = 0;
            let dropped = 0;

            AppState.shows.forEach(s => {
                totalEpisodes += (s.total_episodes || 0);
                episodesWatched += (s.episodes_watched || 0);
                if (s.status === 'WATCHING') watching++;
                else if (s.status === 'COMPLETED') completed++;
                else if (s.status === 'PLAN_TO_WATCH') plan++;
                else if (s.status === 'ON_HOLD') hold++;
                else if (s.status === 'DROPPED') dropped++;
            });

            const completionPct = totalEpisodes > 0 ? Math.round((episodesWatched / totalEpisodes) * 100) : 0;
            const hours = Math.round((episodesWatched * 45) / 60);

            stats = {
                total_shows: AppState.shows.length,
                watching_count: watching,
                completed_count: completed,
                plan_to_watch_count: plan,
                on_hold_count: hold,
                dropped_count: dropped,
                total_episodes: totalEpisodes,
                episodes_watched: episodesWatched,
                completion_pct: completionPct,
                estimated_hours: hours,
            };
        }

        if (elements.statTotalShows) elements.statTotalShows.textContent = stats.total_shows;
        if (elements.statWatchingCount) elements.statWatchingCount.textContent = stats.watching_count;
        if (elements.statCompletedCount) elements.statCompletedCount.textContent = stats.completed_count;
        if (elements.statEpisodesWatched) elements.statEpisodesWatched.textContent = stats.episodes_watched;
        if (elements.statTotalEpisodes) elements.statTotalEpisodes.textContent = stats.total_episodes;
        if (elements.statCompletionPct) elements.statCompletionPct.textContent = `${stats.completion_pct}%`;
        if (elements.statProgressBar) elements.statProgressBar.style.width = `${stats.completion_pct}%`;
        if (elements.statHours) elements.statHours.textContent = stats.estimated_hours;

        // Tab counts
        if (elements.countAll) elements.countAll.textContent = stats.total_shows;
        if (elements.countWatching) elements.countWatching.textContent = stats.watching_count;
        if (elements.countPlan) elements.countPlan.textContent = stats.plan_to_watch_count;
        if (elements.countCompleted) elements.countCompleted.textContent = stats.completed_count;
        if (elements.countHold) elements.countHold.textContent = stats.on_hold_count;
        if (elements.countDropped) elements.countDropped.textContent = stats.dropped_count;
    }

    // Filter and Sort Shows
    function getFilteredShows() {
        let list = [...AppState.shows];

        // Status Filter
        if (AppState.currentFilter !== 'ALL') {
            list = list.filter(s => s.status === AppState.currentFilter);
        }

        // Search Filter
        if (AppState.currentSearch) {
            const q = AppState.currentSearch.toLowerCase();
            list = list.filter(s => {
                return (s.title && s.title.toLowerCase().includes(q)) ||
                       (s.platform && s.platform.toLowerCase().includes(q)) ||
                       (s.genres && s.genres.toLowerCase().includes(q)) ||
                       (s.notes && s.notes.toLowerCase().includes(q));
            });
        }

        // Sorting
        list.sort((a, b) => {
            switch (AppState.currentSort) {
                case 'title_asc':
                    return (a.title || '').localeCompare(b.title || '');
                case 'progress_desc':
                    return (b.progress_percentage || 0) - (a.progress_percentage || 0);
                case 'progress_asc':
                    return (a.progress_percentage || 0) - (b.progress_percentage || 0);
                case 'rating_desc':
                    return (b.rating || 0) - (a.rating || 0);
                case 'seasons_desc':
                    return (b.total_seasons || 0) - (a.total_seasons || 0);
                case 'updated_desc':
                default:
                    return (b.id || 0) - (a.id || 0);
            }
        });

        return list;
    }

    // Render Master Method
    function renderApp() {
        if (!elements.matrixViewContainer || !elements.cardsViewContainer) return;
        const filteredShows = getFilteredShows();

        if (filteredShows.length === 0) {
            elements.matrixViewContainer.style.display = 'none';
            elements.cardsViewContainer.style.display = 'none';
            if (elements.emptyState) elements.emptyState.style.display = 'block';
            return;
        }

        if (elements.emptyState) elements.emptyState.style.display = 'none';

        if (AppState.viewMode === 'matrix') {
            elements.matrixViewContainer.style.display = 'block';
            elements.cardsViewContainer.style.display = 'none';
            renderMatrixView(filteredShows);
        } else {
            elements.matrixViewContainer.style.display = 'none';
            elements.cardsViewContainer.style.display = 'grid';
            renderCardsView(filteredShows);
        }
    }

    // Calculate Max Seasons for Table Header
    function getMaxSeasons(showsList) {
        let maxS = 1;
        showsList.forEach(show => {
            const count = (show.seasons && show.seasons.length) || show.total_seasons || 1;
            if (count > maxS) maxS = count;
        });
        return Math.max(maxS, 3);
    }

    // Render Tabular Matrix View
    function renderMatrixView(showsList) {
        const maxSeasons = getMaxSeasons(showsList);

        // Render Season Headers
        elements.seasonHeadersWrap.setAttribute('colspan', maxSeasons);
        let headerHtml = '';
        for (let i = 1; i <= maxSeasons; i++) {
            headerHtml += `<span class="season-th-cell font-mono">S${i}</span>`;
        }
        elements.seasonHeadersList.innerHTML = headerHtml;

        // Render Body Rows
        let tbodyHtml = '';
        showsList.forEach(show => {
            tbodyHtml += buildMatrixRowHtml(show, maxSeasons);
        });
        elements.matrixTableBody.innerHTML = tbodyHtml;
    }

    function buildMatrixRowHtml(show, maxSeasons) {
        const seasonsMap = {};
        if (show.seasons && Array.isArray(show.seasons)) {
            show.seasons.forEach(s => {
                seasonsMap[s.season_number] = s;
            });
        }

        // Poster image or fallback
        const posterHtml = show.poster_url
            ? `<img src="${escapeHtml(show.poster_url)}" alt="${escapeHtml(show.title)}" class="show-thumb-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
               <div class="show-thumb-fallback" style="display:none;">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`
            : `<div class="show-thumb-fallback">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`;

        // Rating
        const ratingVal = show.rating ? Number(show.rating).toFixed(1) : '—';

        // Status Label & formatting
        const statusDisplay = show.status_display || formatStatus(show.status);

        // Progress Text
        const progressPct = show.progress_percentage || 0;
        const progressLabel = show.current_progress_label || `${show.episodes_watched || 0}/${show.total_episodes || 0}`;

        // Season Cells
        let seasonCellsHtml = '';
        for (let sNum = 1; sNum <= maxSeasons; sNum++) {
            const season = seasonsMap[sNum];
            if (season) {
                const isComplete = season.is_completed || (season.episodes_watched >= season.total_episodes && season.total_episodes > 0);
                const inProgress = !isComplete && season.episodes_watched > 0;
                const pillClass = isComplete ? 'completed' : inProgress ? 'in-progress' : '';
                const pct = season.progress_pct || 0;

                const checkIcon = isComplete
                    ? `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`
                    : '';

                seasonCellsHtml += `
                    <td class="season-matrix-cell">
                        <button type="button" 
                                class="season-pill-btn ${pillClass}" 
                                data-season-id="${season.id}" 
                                data-show-id="${show.id}" 
                                data-season-num="${sNum}"
                                title="Season ${sNum}: ${season.episodes_watched}/${season.total_episodes} Episodes (Click to adjust)">
                            <span>${season.episodes_watched}/${season.total_episodes}</span>
                            ${checkIcon}
                            ${inProgress ? `<span class="season-pill-mini-bar" style="width:${pct}%"></span>` : ''}
                        </button>
                    </td>
                `;
            } else {
                seasonCellsHtml += `
                    <td class="season-matrix-cell">
                        <span class="season-empty-dash">—</span>
                    </td>
                `;
            }
        }

        return `
            <tr data-show-id="${show.id}">
                <!-- Sticky Show Column -->
                <td class="col-sticky col-show">
                    <div class="show-cell-wrap">
                        <div class="show-thumb-wrap" onclick="window.TrackerApp.openDetailModal(${show.id})">
                            ${posterHtml}
                        </div>
                        <div class="show-info-text">
                            <div class="show-title-row">
                                <a href="javascript:void(0)" class="show-title-link" onclick="window.TrackerApp.openDetailModal(${show.id})">${escapeHtml(show.title)}</a>
                                ${show.release_year ? `<span class="show-year">${show.release_year}</span>` : ''}
                            </div>
                            <div class="show-meta-row">
                                ${show.platform ? `<span class="platform-badge">${escapeHtml(show.platform)}</span>` : ''}
                                ${show.genres ? `<span class="genre-text" title="${escapeHtml(show.genres)}">${escapeHtml(show.genres)}</span>` : ''}
                            </div>
                        </div>
                    </div>
                </td>

                <!-- Rating -->
                <td class="col-rating font-mono">
                    <span class="rating-pill">★ ${ratingVal}</span>
                </td>

                <!-- Status -->
                <td class="col-status">
                    <span class="status-badge" data-status="${show.status}">
                        <span class="status-dot"></span>
                        <span>${escapeHtml(statusDisplay)}</span>
                    </span>
                </td>

                <!-- Progress -->
                <td class="col-progress">
                    <div class="progress-cell-wrap">
                        <div class="progress-label-row">
                            <span>${escapeHtml(progressLabel)}</span>
                            <span class="progress-pct-val">${progressPct}%</span>
                        </div>
                        <div class="progress-track">
                            <div class="progress-fill" style="width: ${progressPct}%;"></div>
                        </div>
                    </div>
                </td>

                <!-- Season Cells -->
                ${seasonCellsHtml}

                <!-- Actions -->
                <td class="col-actions">
                    <div class="actions-cell-wrap">
                        <button type="button" class="btn-step-pill" title="Advance +1 Episode" onclick="window.TrackerApp.stepQuickEpisode(${show.id}, 1)" aria-label="Step +1 Episode">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                            <span>+1 Ep</span>
                        </button>
                        <button type="button" class="btn-icon" title="View details" onclick="window.TrackerApp.openDetailModal(${show.id})" aria-label="Show details">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                        </button>
                        <button type="button" class="btn-icon" title="Edit show" onclick="window.TrackerApp.openEditModal(${show.id})" aria-label="Edit show">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"></path></svg>
                        </button>
                        <button type="button" class="btn-icon btn-icon-danger" title="Delete show" onclick="window.TrackerApp.openDeleteModal(${show.id})" aria-label="Delete show">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    // Render Cards Grid View
    function renderCardsView(showsList) {
        let cardsHtml = '';
        showsList.forEach(show => {
            const posterHtml = show.poster_url
                ? `<img src="${escapeHtml(show.poster_url)}" alt="${escapeHtml(show.title)}" class="card-poster-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                   <div class="card-poster-fallback" style="display:none;">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`
                : `<div class="card-poster-fallback">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`;

            const statusDisplay = show.status_display || formatStatus(show.status);
            const ratingVal = show.rating ? Number(show.rating).toFixed(1) : null;
            const progressPct = show.progress_percentage || 0;

            let seasonsPills = '';
            if (show.seasons && Array.isArray(show.seasons)) {
                show.seasons.forEach(s => {
                    const isComplete = s.is_completed || (s.episodes_watched >= s.total_episodes && s.total_episodes > 0);
                    const inProg = !isComplete && s.episodes_watched > 0;
                    const pillClass = isComplete ? 'completed' : inProg ? 'in-progress' : '';
                    seasonsPills += `
                        <button type="button" class="season-pill-btn card-season-pill ${pillClass}"
                                data-season-id="${s.id}" data-show-id="${show.id}" data-season-num="${s.season_number}">
                            S${s.season_number}: ${s.episodes_watched}/${s.total_episodes}
                        </button>
                    `;
                });
            }

            cardsHtml += `
                <div class="show-card" data-show-id="${show.id}">
                    <div class="card-poster-area" onclick="window.TrackerApp.openDetailModal(${show.id})" style="cursor:pointer;">
                        ${posterHtml}
                        <div class="card-badge-top">
                            <span class="status-badge" data-status="${show.status}">
                                <span class="status-dot"></span>
                                <span>${escapeHtml(statusDisplay)}</span>
                            </span>
                        </div>
                        ${ratingVal ? `<div class="card-rating-top">★ ${ratingVal}</div>` : ''}
                    </div>

                    <div class="card-body">
                        <div class="card-title-box">
                            <h4 class="card-title">${escapeHtml(show.title)}</h4>
                            <div class="card-meta-text">
                                ${show.release_year ? `${show.release_year} &bull; ` : ''}
                                ${show.platform ? `${escapeHtml(show.platform)}` : ''}
                            </div>
                        </div>

                        <div class="progress-cell-wrap">
                            <div class="progress-label-row">
                                <span>${escapeHtml(show.current_progress_label || '')}</span>
                                <span class="progress-pct-val">${progressPct}%</span>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill" style="width: ${progressPct}%;"></div>
                            </div>
                        </div>

                        <div class="card-seasons-pills">
                            ${seasonsPills}
                        </div>
                    </div>

                    <div class="card-footer">
                        <button type="button" class="btn-step-pill" onclick="window.TrackerApp.stepQuickEpisode(${show.id}, 1)" title="Advance +1 Episode">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                            <span>+1 Episode</span>
                        </button>
                        <div class="actions-cell-wrap">
                            <button type="button" class="btn-icon" title="View details" onclick="window.TrackerApp.openDetailModal(${show.id})" aria-label="Show details">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                            </button>
                            <button type="button" class="btn-icon" title="Edit show" onclick="window.TrackerApp.openEditModal(${show.id})" aria-label="Edit show">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"></path></svg>
                            </button>
                            <button type="button" class="btn-icon btn-icon-danger" title="Delete show" onclick="window.TrackerApp.openDeleteModal(${show.id})" aria-label="Delete show">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        elements.cardsViewContainer.innerHTML = cardsHtml;
    }

    function formatStatus(status) {
        switch (status) {
            case 'WATCHING': return 'Watching';
            case 'PLAN_TO_WATCH': return 'Plan to Watch';
            case 'COMPLETED': return 'Completed';
            case 'ON_HOLD': return 'On Hold';
            case 'DROPPED': return 'Dropped';
            default: return status || 'Unknown';
        }
    }

    // =========================================================================
    // INTERACTIVE SEASON POPOVER DROPDOWN
    // =========================================================================
    function openSeasonPopover(buttonEl, seasonId, showId) {
        if (!SpamGuard.acquire('open_popover', 120)) return;
        const show = AppState.shows.find(s => s.id === Number(showId));
        if (!show || !show.seasons) return;
        const season = show.seasons.find(s => s.id === Number(seasonId));
        if (!season) return;

        AppState.activePopover = {
            seasonId: season.id,
            showId: show.id,
            buttonEl: buttonEl,
            season: season,
            show: show,
        };

        // Populate popover
        elements.popoverSeasonTitle.textContent = `${show.title} — Season ${season.season_number}`;
        elements.popoverSeasonSub.textContent = `${season.episodes_watched} of ${season.total_episodes} episodes watched (${season.progress_pct || 0}%)`;

        const progFill = document.getElementById('popover-progress-fill');
        if (progFill) progFill.style.width = `${season.progress_pct || 0}%`;

        const isComplete = season.episodes_watched >= season.total_episodes;
        elements.popoverToggleText.textContent = isComplete ? 'Reset Season' : 'Complete Season';

        const resetZeroBtn = document.getElementById('popover-btn-reset-zero');
        if (resetZeroBtn) {
            resetZeroBtn.style.opacity = season.episodes_watched > 0 ? '1' : '0.4';
            resetZeroBtn.style.pointerEvents = season.episodes_watched > 0 ? 'auto' : 'none';
        }

        // Adjust column count based on episode count
        if (season.total_episodes <= 5) {
            elements.popoverEpisodesGrid.style.gridTemplateColumns = 'repeat(5, 1fr)';
        } else if (season.total_episodes <= 10) {
            elements.popoverEpisodesGrid.style.gridTemplateColumns = 'repeat(5, 1fr)';
        } else {
            elements.popoverEpisodesGrid.style.gridTemplateColumns = 'repeat(6, 1fr)';
        }

        // Render Episode Grid Chips (Clean 1 to N, no awkward 0 offset)
        let gridHtml = '';
        for (let ep = 1; ep <= season.total_episodes; ep++) {
            const isActive = (season.episodes_watched === ep);
            const isWatched = (ep <= season.episodes_watched);
            const chipClass = isActive ? 'active' : (isWatched ? 'watched' : '');
            gridHtml += `
                <button type="button" class="ep-chip-btn ${chipClass}" data-ep="${ep}" title="Episode ${ep}${isActive ? ' (Current)' : (isWatched ? ' (Watched)' : '')}">
                    ${ep}
                </button>
            `;
        }
        elements.popoverEpisodesGrid.innerHTML = gridHtml;

        // Position Popover
        const rect = buttonEl.getBoundingClientRect();
        const popoverWidth = 320;

        let left = rect.left + (rect.width / 2) - (popoverWidth / 2) + window.scrollX;
        let top = rect.bottom + 8 + window.scrollY;

        // Boundary checks
        if (left < 16) left = 16;
        if (left + popoverWidth > window.innerWidth - 16) {
            left = window.innerWidth - popoverWidth - 16;
        }

        elements.seasonPopover.style.left = `${left}px`;
        elements.seasonPopover.style.top = `${top}px`;
        elements.seasonPopover.style.display = 'block';
    }

    function closeSeasonPopover() {
        elements.seasonPopover.style.display = 'none';
        AppState.activePopover = null;
    }

    // Optimistic Update Season Episode (0ms latency feedback)
    async function updateSeasonEpisodeCount(seasonId, newEpCount) {
        if (!SpamGuard.acquire(`ep_count_${seasonId}`, 180)) return;
        const showIdx = AppState.shows.findIndex(s => s.seasons && s.seasons.some(sn => sn.id === Number(seasonId)));
        if (showIdx === -1) return;

        // Clone previous state for rollback
        const previousShows = JSON.parse(JSON.stringify(AppState.shows));
        const show = AppState.shows[showIdx];
        const season = show.seasons.find(sn => sn.id === Number(seasonId));
        if (!season) return;

        // 1. Optimistic Mutation
        season.episodes_watched = Math.max(0, Math.min(season.total_episodes, newEpCount));
        recalculateShowProgress(show);
        updateStatsUI();
        renderApp();

        // Update popover if open
        if (AppState.activePopover && AppState.activePopover.seasonId === Number(seasonId)) {
            const btn = document.querySelector(`[data-season-id="${seasonId}"]`);
            if (btn) openSeasonPopover(btn, seasonId, show.id);
        }

        Loading.start();
        try {
            const res = await fetch(`/api/seasons/${seasonId}/update-episode/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ episodes_watched: newEpCount })
            });
            const data = await res.json();
            if (data.success) {
                // Reconcile authoritative state
                AppState.shows[showIdx] = data.show;
                updateStatsUI(data.stats);
                renderApp();
            } else {
                // Rollback on server validation error
                AppState.shows = previousShows;
                updateStatsUI();
                renderApp();
                showToast(data.error || 'Failed to update episode', 'error');
            }
        } catch (err) {
            console.error('Network error during updateSeasonEpisodeCount:', err);
            // Rollback on network failure
            AppState.shows = previousShows;
            updateStatsUI();
            renderApp();
            showToast('Network error while updating episode', 'error');
        } finally {
            Loading.done();
        }
    }

    // Optimistic Toggle Season Complete (0ms latency feedback)
    async function toggleSeasonComplete(seasonId) {
        if (!SpamGuard.acquire(`season_toggle_${seasonId}`, 300)) return;
        const showIdx = AppState.shows.findIndex(s => s.seasons && s.seasons.some(sn => sn.id === Number(seasonId)));
        if (showIdx === -1) return;

        const previousShows = JSON.parse(JSON.stringify(AppState.shows));
        const show = AppState.shows[showIdx];
        const season = show.seasons.find(sn => sn.id === Number(seasonId));
        if (!season) return;

        // 1. Optimistic Mutation
        if (season.episodes_watched >= season.total_episodes) {
            season.episodes_watched = 0;
        } else {
            season.episodes_watched = season.total_episodes;
        }
        recalculateShowProgress(show);
        updateStatsUI();
        renderApp();

        if (AppState.activePopover && AppState.activePopover.seasonId === Number(seasonId)) {
            const btn = document.querySelector(`[data-season-id="${seasonId}"]`);
            if (btn) openSeasonPopover(btn, seasonId, show.id);
        }

        Loading.start();
        try {
            const res = await fetch(`/api/seasons/${seasonId}/toggle-complete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                }
            });
            const data = await res.json();
            if (data.success) {
                AppState.shows[showIdx] = data.show;
                updateStatsUI(data.stats);
                renderApp();
                const msg = data.season.is_completed ? `Marked S${data.season.season_number} Complete!` : `Reset S${data.season.season_number} to 0`;
                showToast(msg, 'success');
            } else {
                AppState.shows = previousShows;
                updateStatsUI();
                renderApp();
                showToast(data.error || 'Error toggling season', 'error');
            }
        } catch (err) {
            console.error(err);
            AppState.shows = previousShows;
            updateStatsUI();
            renderApp();
            showToast('Error toggling season completion', 'error');
        } finally {
            Loading.done();
        }
    }

    // Optimistic Step Quick Episode (+1 or -1)
    async function stepQuickEpisode(showId, direction) {
        if (!SpamGuard.acquire(`step_${showId}`, 220)) return;
        const showIdx = AppState.shows.findIndex(s => s.id === Number(showId));
        if (showIdx === -1) return;

        const previousShows = JSON.parse(JSON.stringify(AppState.shows));
        const show = AppState.shows[showIdx];
        if (!show.seasons || show.seasons.length === 0) return;

        // Optimistic Step
        show.seasons.sort((a, b) => (a.season_number || 0) - (b.season_number || 0));
        let targetSeason = null;
        if (direction > 0) {
            for (const s of show.seasons) {
                if (s.episodes_watched < s.total_episodes) {
                    targetSeason = s;
                    break;
                }
            }
            if (!targetSeason) targetSeason = show.seasons[show.seasons.length - 1];
            else targetSeason.episodes_watched += 1;
        } else {
            for (let i = show.seasons.length - 1; i >= 0; i--) {
                if (show.seasons[i].episodes_watched > 0) {
                    targetSeason = show.seasons[i];
                    break;
                }
            }
            if (targetSeason) targetSeason.episodes_watched -= 1;
        }

        recalculateShowProgress(show);
        updateStatsUI();
        renderApp();

        Loading.start();
        try {
            const res = await fetch(`/api/shows/${showId}/quick-step/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ direction: direction })
            });
            const data = await res.json();
            if (data.success) {
                AppState.shows[showIdx] = data.show;
                updateStatsUI(data.stats);
                renderApp();
            } else {
                AppState.shows = previousShows;
                updateStatsUI();
                renderApp();
                showToast(data.error || 'Error stepping episode', 'error');
            }
        } catch (err) {
            console.error(err);
            AppState.shows = previousShows;
            updateStatsUI();
            renderApp();
            showToast('Error stepping episode', 'error');
        } finally {
            Loading.done();
        }
    }

    // =========================================================================
    // ADD / EDIT SHOW MODAL & SEASONS BUILDER
    // =========================================================================
    function updatePosterPreview(url) {
        if (!elements.formPosterPreview) return;
        if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
            elements.formPosterImg.src = url;
            elements.formPosterPreview.style.display = 'block';
        } else {
            elements.formPosterPreview.style.display = 'none';
        }
    }

    function openAddModal() {
        if (!SpamGuard.acquire('modal_open', 200)) return;
        AppState.editingShowId = null;
        elements.formModalTitle.textContent = 'Add New Show';
        elements.formShowId.value = '';
        elements.formTitle.value = '';
        elements.formYear.value = new Date().getFullYear();
        elements.formPoster.value = '';
        updatePosterPreview('');
        elements.formPlatform.value = '';
        elements.formStatus.value = 'WATCHING';
        elements.formRating.value = '';
        elements.formGenres.value = '';
        elements.formNotes.value = '';
        closeAutocomplete();

        // Default 1 Season with 10 eps
        renderSeasonBuilderRows([{ season_number: 1, total_episodes: 10, episodes_watched: 0 }]);
        elements.showFormModal.style.display = 'flex';
        setTimeout(() => elements.formTitle.focus(), 50);
    }

    function openEditModal(showId) {
        if (!SpamGuard.acquire('modal_open', 200)) return;
        const show = AppState.shows.find(s => s.id === Number(showId));
        if (!show) return;

        closeDetailModal();
        closeSeasonPopover();
        closeAutocomplete();

        AppState.editingShowId = show.id;
        elements.formModalTitle.textContent = `Edit "${show.title}"`;
        elements.formShowId.value = show.id;
        elements.formTitle.value = show.title || '';
        elements.formYear.value = show.release_year || '';
        elements.formPoster.value = show.poster_url || '';
        updatePosterPreview(show.poster_url || '');
        elements.formPlatform.value = show.platform || '';
        elements.formStatus.value = show.status || 'WATCHING';
        elements.formRating.value = show.rating ? Number(show.rating) : '';
        elements.formGenres.value = show.genres || '';
        elements.formNotes.value = show.notes || '';

        const seasons = (show.seasons && show.seasons.length)
            ? show.seasons
            : [{ season_number: 1, total_episodes: 10, episodes_watched: 0 }];
        renderSeasonBuilderRows(seasons);

        elements.showFormModal.style.display = 'flex';
        setTimeout(() => elements.formTitle.focus(), 50);
    }

    // =========================================================================
    // LIVE EXTERNAL SHOW SEARCH (IMDb / TV DATABASE AUTOCOMPLETE WITH CACHING)
    // =========================================================================
    let autocompleteTimer = null;

    async function searchExternalShows(query) {
        if (!query || query.trim().length < 2) {
            closeAutocomplete();
            return;
        }

        const cleanQ = query.trim().toLowerCase();

        // Instant 0ms response from client memory cache
        if (searchCache.has(cleanQ)) {
            renderAutocompleteDropdown(searchCache.get(cleanQ));
            return;
        }

        if (elements.autocompleteSpinner) elements.autocompleteSpinner.style.display = 'block';
        Loading.start();

        try {
            const res = await fetch(`/api/search-external-shows/?q=${encodeURIComponent(query.trim())}`);
            const data = await res.json();
            if (data.success && Array.isArray(data.results)) {
                searchCache.set(cleanQ, data.results);
                renderAutocompleteDropdown(data.results);
            } else {
                closeAutocomplete();
            }
        } catch (err) {
            console.error('Error in searchExternalShows:', err);
            closeAutocomplete();
        } finally {
            if (elements.autocompleteSpinner) elements.autocompleteSpinner.style.display = 'none';
            Loading.done();
        }
    }

    function renderAutocompleteDropdown(results) {
        if (!elements.autocompleteDropdown) return;
        if (!results || results.length === 0) {
            elements.autocompleteDropdown.innerHTML = '<div class="ac-empty">No shows found. You can type details manually.</div>';
            elements.autocompleteDropdown.style.display = 'block';
            return;
        }

        let html = '';
        results.forEach(show => {
            const isAlreadyTracked = AppState.shows.some(s => 
                s.title.toLowerCase().trim() === show.title.toLowerCase().trim()
            );

            const thumbHtml = show.thumb_url
                ? `<img src="${escapeHtml(show.thumb_url)}" alt="${escapeHtml(show.title)}" class="ac-thumb" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                   <div class="ac-thumb-fallback" style="display:none;">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`
                : `<div class="ac-thumb-fallback">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`;

            const ratingVal = show.rating ? `★ ${Number(show.rating).toFixed(1)}` : '';
            const metaInfo = [
                show.platform ? escapeHtml(show.platform) : '',
                show.genres ? escapeHtml(show.genres.split(',')[0]) : ''
            ].filter(Boolean).join(' • ');

            html += `
                <div class="ac-item ${isAlreadyTracked ? 'ac-item-tracked' : ''}" data-tvmaze-id="${show.id}" tabindex="0" role="option">
                    ${thumbHtml}
                    <div class="ac-info">
                        <div class="ac-title-row">
                            <span class="ac-title">${escapeHtml(show.title)}</span>
                            ${show.year ? `<span class="ac-year">(${show.year})</span>` : ''}
                            ${isAlreadyTracked ? `<span class="ac-badge-tracked">In Tracker</span>` : ''}
                        </div>
                        <div class="ac-meta">
                            ${ratingVal ? `<span class="ac-rating font-mono">${ratingVal}</span>` : ''}
                            ${metaInfo ? `<span>${metaInfo}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });

        elements.autocompleteDropdown.innerHTML = html;
        elements.autocompleteDropdown.style.display = 'block';
    }

    function closeAutocomplete() {
        if (elements.autocompleteDropdown) {
            elements.autocompleteDropdown.style.display = 'none';
            elements.autocompleteDropdown.innerHTML = '';
        }
        if (elements.autocompleteSpinner) {
            elements.autocompleteSpinner.style.display = 'none';
        }
    }

    async function selectExternalShow(tvmazeId) {
        closeAutocomplete();

        // Check client details cache
        if (detailsCache.has(String(tvmazeId))) {
            const data = detailsCache.get(String(tvmazeId));
            applyFetchedShowData(data);
            showToast(`Auto-filled "${data.title}" with ${data.seasons.length} seasons & episode counts!`, 'success');
            return;
        }

        showToast('Fetching metadata and season episode breakdown...', 'info');
        Loading.start();

        try {
            const res = await fetch(`/api/fetch-external-show-details/?id=${tvmazeId}`);
            const data = await res.json();
            if (data.success) {
                detailsCache.set(String(tvmazeId), data);
                applyFetchedShowData(data);
                showToast(`Auto-filled "${data.title}" with ${data.seasons.length} seasons & episode counts!`, 'success');
            } else {
                showToast(data.error || 'Failed to fetch details', 'error');
            }
        } catch (err) {
            console.error(err);
            showToast('Error auto-filling show details', 'error');
        } finally {
            Loading.done();
        }
    }

    function applyFetchedShowData(data) {
        elements.formTitle.value = data.title || '';
        elements.formYear.value = data.release_year || '';
        elements.formPoster.value = data.poster_url || '';
        updatePosterPreview(data.poster_url || '');
        elements.formPlatform.value = data.platform || '';
        elements.formStatus.value = data.status || 'WATCHING';
        elements.formRating.value = data.rating ? Number(data.rating).toFixed(1) : '';
        elements.formGenres.value = data.genres || '';
        elements.formNotes.value = data.notes || '';

        if (data.seasons && data.seasons.length > 0) {
            renderSeasonBuilderRows(data.seasons);
        }
    }

    function closeFormModal() {
        elements.showFormModal.style.display = 'none';
        AppState.editingShowId = null;
    }

    function renderSeasonBuilderRows(seasons) {
        let html = '';
        seasons.forEach((s, idx) => {
            const sNum = idx + 1;
            html += `
                <div class="season-builder-row" data-snum="${sNum}">
                    <span class="sb-season-label font-mono">S${sNum}</span>
                    <div class="sb-input-wrap">
                        <label class="sb-input-label">Total Eps:</label>
                        <input type="number" class="sb-input sb-total-eps font-mono" value="${s.total_episodes || 10}" min="1" max="999">
                    </div>
                    <div class="sb-input-wrap">
                        <label class="sb-input-label">Watched:</label>
                        <input type="number" class="sb-input sb-watched-eps font-mono" value="${s.episodes_watched || 0}" min="0" max="999">
                    </div>
                    <button type="button" class="sb-remove-btn" onclick="this.closest('.season-builder-row').remove(); window.TrackerApp.reindexSeasonBuilderRows();" title="Remove Season">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
            `;
        });
        elements.seasonsRowsContainer.innerHTML = html;
    }

    function addSeasonBuilderRow() {
        if (!SpamGuard.acquire('add_season_row', 150)) return;
        const rows = elements.seasonsRowsContainer.querySelectorAll('.season-builder-row');
        const nextNum = rows.length + 1;
        const row = document.createElement('div');
        row.className = 'season-builder-row';
        row.dataset.snum = nextNum;
        row.innerHTML = `
            <span class="sb-season-label font-mono">S${nextNum}</span>
            <div class="sb-input-wrap">
                <label class="sb-input-label">Total Eps:</label>
                <input type="number" class="sb-input sb-total-eps font-mono" value="10" min="1" max="999">
            </div>
            <div class="sb-input-wrap">
                <label class="sb-input-label">Watched:</label>
                <input type="number" class="sb-input sb-watched-eps font-mono" value="0" min="0" max="999">
            </div>
            <button type="button" class="sb-remove-btn" onclick="this.closest('.season-builder-row').remove(); window.TrackerApp.reindexSeasonBuilderRows();" title="Remove Season">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
        `;
        elements.seasonsRowsContainer.appendChild(row);
    }

    function reindexSeasonBuilderRows() {
        const rows = elements.seasonsRowsContainer.querySelectorAll('.season-builder-row');
        rows.forEach((r, idx) => {
            const num = idx + 1;
            r.dataset.snum = num;
            const label = r.querySelector('.sb-season-label');
            if (label) label.textContent = `S${num}`;
        });
    }

    async function handleShowFormSubmit(e) {
        e.preventDefault();

        if (!SpamGuard.acquire('form_submit', 1000)) return;

        const title = elements.formTitle.value.trim();
        if (!title) {
            showToast('Show title is required', 'error');
            elements.formTitle.focus();
            return;
        }

        const showId = elements.formShowId.value ? Number(elements.formShowId.value) : null;
        const isEdit = Boolean(showId);

        // Client-side duplicate check
        const isDuplicate = AppState.shows.some(s => 
            s.title.toLowerCase().trim() === title.toLowerCase() && 
            (!showId || s.id !== showId)
        );

        if (isDuplicate) {
            showToast(`A show titled "${title}" is already in your tracker.`, 'error');
            elements.formTitle.focus();
            elements.formTitle.classList.add('input-error');
            setTimeout(() => elements.formTitle.classList.remove('input-error'), 2000);
            return;
        }

        // Collect season rows
        const seasonRows = elements.seasonsRowsContainer.querySelectorAll('.season-builder-row');
        const seasons = [];
        seasonRows.forEach((r, idx) => {
            const total = parseInt(r.querySelector('.sb-total-eps').value, 10) || 10;
            const watched = parseInt(r.querySelector('.sb-watched-eps').value, 10) || 0;
            seasons.push({
                season_number: idx + 1,
                total_episodes: Math.max(1, total),
                episodes_watched: Math.max(0, Math.min(total, watched))
            });
        });

        if (seasons.length === 0) {
            seasons.push({ season_number: 1, total_episodes: 10, episodes_watched: 0 });
        }

        const payload = {
            title: title,
            release_year: elements.formYear.value ? parseInt(elements.formYear.value, 10) : null,
            poster_url: elements.formPoster.value.trim() || null,
            platform: elements.formPlatform.value.trim(),
            status: elements.formStatus.value,
            rating: elements.formRating.value ? parseFloat(elements.formRating.value) : 0.0,
            genres: elements.formGenres.value.trim(),
            notes: elements.formNotes.value.trim(),
            total_seasons: seasons.length,
            seasons: seasons,
        };

        const endpoint = isEdit ? `/api/shows/${showId}/update/` : '/api/shows/create/';
        const submitBtn = elements.btnSaveShow || elements.showForm?.querySelector('button[type="submit"]');
        Loading.setButtonLoading(submitBtn, true, isEdit ? 'Updating...' : 'Saving...');
        Loading.start();

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                if (isEdit) {
                    const idx = AppState.shows.findIndex(s => s.id === data.show.id);
                    if (idx !== -1) AppState.shows[idx] = data.show;
                } else {
                    AppState.shows.unshift(data.show);
                }
                updateStatsUI(data.stats);
                renderApp();
                closeFormModal();
                showToast(data.message || (isEdit ? 'Show updated!' : 'Show added!'), 'success');
            } else {
                showToast(data.error || 'Validation error', 'error');
            }
        } catch (err) {
            console.error(err);
            showToast('Network error while saving show', 'error');
        } finally {
            Loading.setButtonLoading(submitBtn, false);
            Loading.done();
        }
    }

    // =========================================================================
    // SHOW DETAIL MODAL
    // =========================================================================
    function openDetailModal(showId) {
        if (!SpamGuard.acquire('modal_open', 200)) return;
        const show = AppState.shows.find(s => s.id === Number(showId));
        if (!show) return;

        closeSeasonPopover();

        elements.detailModalTitle.textContent = show.title;
        elements.detailSubMeta.textContent = `${show.release_year || 'N/A'} • ${show.platform || 'No Platform'} • ${show.total_seasons || 1} Seasons`;

        // Poster
        elements.detailPosterBox.innerHTML = show.poster_url
            ? `<img src="${escapeHtml(show.poster_url)}" alt="${escapeHtml(show.title)}" class="detail-poster-img" onerror="this.parentElement.innerHTML='<div class=\\'detail-poster-fallback\\'>${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>';">`
            : `<div class="detail-poster-fallback">${escapeHtml(show.title.substring(0, 2).toUpperCase())}</div>`;

        elements.detailRating.textContent = show.rating ? `★ ${Number(show.rating).toFixed(1)}` : '★ —';
        elements.detailProgress.textContent = `${show.progress_percentage || 0}%`;
        elements.detailStatus.textContent = show.status_display || formatStatus(show.status);

        // Genres
        elements.detailGenres.innerHTML = (show.genres || '')
            .split(',')
            .map(g => g.trim())
            .filter(Boolean)
            .map(g => `<span class="platform-badge">${escapeHtml(g)}</span>`)
            .join(' ');

        // Notes
        elements.detailNotes.textContent = show.notes || 'No notes or personal review recorded for this show yet.';

        // Seasons breakdown
        let seasonsHtml = '';
        if (show.seasons && Array.isArray(show.seasons)) {
            show.seasons.forEach(s => {
                const isComplete = s.is_completed || s.episodes_watched >= s.total_episodes;
                seasonsHtml += `
                    <div class="detail-season-item">
                        <div>
                            <strong>Season ${s.season_number}</strong>: 
                            <span class="font-mono text-muted">${s.episodes_watched} / ${s.total_episodes} Episodes</span>
                        </div>
                        <div>
                            <button type="button" class="btn btn-secondary btn-xs" onclick="window.TrackerApp.toggleSeasonComplete(${s.id})">
                                ${isComplete ? 'Reset' : 'Complete'}
                            </button>
                        </div>
                    </div>
                `;
            });
        }
        elements.detailSeasonsList.innerHTML = seasonsHtml;

        elements.btnDetailEdit.onclick = () => openEditModal(show.id);
        elements.showDetailModal.style.display = 'flex';
    }

    function closeDetailModal() {
        elements.showDetailModal.style.display = 'none';
    }

    // =========================================================================
    // DELETE SHOW CONFIRMATION (OPTIMISTIC REMOVAL)
    // =========================================================================
    function openDeleteModal(showId) {
        if (!SpamGuard.acquire('modal_open', 200)) return;
        const show = AppState.shows.find(s => s.id === Number(showId));
        if (!show) return;

        closeSeasonPopover();
        AppState.deletingShowId = show.id;
        elements.deleteShowTitle.textContent = `"${show.title}"`;
        elements.deleteConfirmModal.style.display = 'flex';
    }

    function closeDeleteModal() {
        elements.deleteConfirmModal.style.display = 'none';
        AppState.deletingShowId = null;
    }

    async function confirmDeleteShow() {
        if (!AppState.deletingShowId) return;
        const showId = AppState.deletingShowId;
        if (!SpamGuard.acquire(`delete_show_${showId}`, 1000)) return;

        const previousShows = [...AppState.shows];

        // 1. Optimistic removal from UI immediately (0ms)
        AppState.shows = AppState.shows.filter(s => s.id !== showId);
        updateStatsUI();
        renderApp();
        closeDeleteModal();

        const deleteBtn = elements.btnConfirmDelete;
        Loading.setButtonLoading(deleteBtn, true, 'Deleting...');
        Loading.start();

        try {
            const res = await fetch(`/api/shows/${showId}/delete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                }
            });
            const data = await res.json();
            if (data.success) {
                updateStatsUI(data.stats);
                showToast(data.message || 'Show deleted', 'info');
            } else {
                // Rollback on server error
                AppState.shows = previousShows;
                updateStatsUI();
                renderApp();
                showToast(data.error || 'Failed to delete show', 'error');
            }
        } catch (err) {
            console.error(err);
            // Rollback on network failure
            AppState.shows = previousShows;
            updateStatsUI();
            renderApp();
            showToast('Error deleting show', 'error');
        } finally {
            Loading.setButtonLoading(deleteBtn, false);
            Loading.done();
        }
    }

    // =========================================================================
    // BACKUP & RESTORE
    // =========================================================================
    function exportBackup() {
        if (!SpamGuard.acquire('export_backup', 1000)) return;
        SpamGuard.guardClick(elements.btnExportJson, 1000);
        showToast('Exporting shows database...', 'info');
        window.location.href = '/api/export-json/';
    }

    async function importBackup(file) {
        if (!SpamGuard.acquire('import_backup', 1000)) return;
        const importBtn = elements.btnImportTrigger;
        Loading.setButtonLoading(importBtn, true, 'Restoring...');
        Loading.start();

        try {
            const text = await file.text();
            const json = JSON.parse(text);
            const res = await fetch('/api/import-json/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(json)
            });
            const data = await res.json();
            if (data.success) {
                AppState.shows = data.shows;
                updateStatsUI(data.stats);
                renderApp();
                showToast(data.message || 'Backup restored successfully!', 'success');
            } else {
                showToast(data.error || 'Invalid backup file structure', 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Failed to parse or import JSON backup', 'error');
        } finally {
            Loading.setButtonLoading(importBtn, false);
            Loading.done();
        }
    }

    async function sendTestEmailDigest() {
        if (!SpamGuard.acquire('email_digest', 2000)) return;
        const digestBtn = document.getElementById('btn-email-digest');
        if (digestBtn) Loading.setButtonLoading(digestBtn, true, 'Sending...');
        Loading.start();

        try {
            const res = await fetch('/api/send-test-digest/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message || `Monthly digest sent to ${data.email || 'your email'}`, 'success');
            } else {
                showToast(data.error || 'Failed to send email digest', 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Network error while requesting email digest', 'error');
        } finally {
            if (digestBtn) Loading.setButtonLoading(digestBtn, false);
            Loading.done();
        }
    }

    // =========================================================================
    // EVENT LISTENERS & INITIALIZATION
    // =========================================================================
    function setupEventListeners() {
        // Tab Filters
        if (elements.filterTabs && elements.filterTabs.length) {
            elements.filterTabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    if (!SpamGuard.acquire('filter_tab', 120)) return;
                    SpamGuard.guardClick(tab, 120);
                    elements.filterTabs.forEach(t => {
                        t.classList.remove('active');
                        t.setAttribute('aria-selected', 'false');
                    });
                    tab.classList.add('active');
                    tab.setAttribute('aria-selected', 'true');
                    AppState.currentFilter = tab.dataset.status;
                    closeSeasonPopover();
                    renderApp();
                });
            });
        }

        // Search Input
        let searchDebounceTimer = null;
        if (elements.searchInput) {
            elements.searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounceTimer);
                const val = e.target.value.trim();
                if (elements.searchClearBtn) elements.searchClearBtn.style.display = val ? 'flex' : 'none';
                searchDebounceTimer = setTimeout(() => {
                    AppState.currentSearch = val;
                    closeSeasonPopover();
                    renderApp();
                }, 100);
            });
        }

        if (elements.searchClearBtn) {
            elements.searchClearBtn.addEventListener('click', () => {
                if (!SpamGuard.acquire('search_clear', 120)) return;
                SpamGuard.guardClick(elements.searchClearBtn, 120);
                if (elements.searchInput) elements.searchInput.value = '';
                elements.searchClearBtn.style.display = 'none';
                AppState.currentSearch = '';
                closeSeasonPopover();
                renderApp();
                if (elements.searchInput) elements.searchInput.focus();
            });
        }

        // Sort Select
        if (elements.sortSelect) {
            elements.sortSelect.addEventListener('change', (e) => {
                AppState.currentSort = e.target.value;
                closeSeasonPopover();
                renderApp();
            });
        }

        // View Mode Switcher
        if (elements.btnViewMatrix) {
            elements.btnViewMatrix.addEventListener('click', () => {
                if (!SpamGuard.acquire('view_mode', 120)) return;
                SpamGuard.guardClick(elements.btnViewMatrix, 120);
                AppState.viewMode = 'matrix';
                elements.btnViewMatrix.classList.add('active');
                elements.btnViewMatrix.setAttribute('aria-pressed', 'true');
                if (elements.btnViewCards) {
                    elements.btnViewCards.classList.remove('active');
                    elements.btnViewCards.setAttribute('aria-pressed', 'false');
                }
                closeSeasonPopover();
                renderApp();
            });
        }

        if (elements.btnViewCards) {
            elements.btnViewCards.addEventListener('click', () => {
                if (!SpamGuard.acquire('view_mode', 120)) return;
                SpamGuard.guardClick(elements.btnViewCards, 120);
                AppState.viewMode = 'cards';
                elements.btnViewCards.classList.add('active');
                elements.btnViewCards.setAttribute('aria-pressed', 'true');
                if (elements.btnViewMatrix) {
                    elements.btnViewMatrix.classList.remove('active');
                    elements.btnViewMatrix.setAttribute('aria-pressed', 'false');
                }
                closeSeasonPopover();
                renderApp();
            });
        }

        // Add Show Button & Form
        if (elements.btnOpenAddModal) {
            elements.btnOpenAddModal.addEventListener('click', () => {
                SpamGuard.guardClick(elements.btnOpenAddModal, 200);
                openAddModal();
            });
        }
        if (elements.btnEmptyAdd) {
            elements.btnEmptyAdd.addEventListener('click', () => {
                SpamGuard.guardClick(elements.btnEmptyAdd, 200);
                openAddModal();
            });
        }
        if (elements.btnCloseFormModal) elements.btnCloseFormModal.addEventListener('click', closeFormModal);
        if (elements.btnCancelForm) elements.btnCancelForm.addEventListener('click', closeFormModal);
        if (elements.showForm) elements.showForm.addEventListener('submit', handleShowFormSubmit);
        if (elements.btnAddSeasonRow) elements.btnAddSeasonRow.addEventListener('click', addSeasonBuilderRow);

        // Poster input preview
        if (elements.formPoster) {
            elements.formPoster.addEventListener('input', (e) => {
                updatePosterPreview(e.target.value.trim());
            });
        }

        // Live IMDb/TV Autocomplete search on typing show title with caching
        if (elements.formTitle) {
            elements.formTitle.addEventListener('input', (e) => {
                if (AppState.editingShowId) return;

                clearTimeout(autocompleteTimer);
                const query = e.target.value;
                autocompleteTimer = setTimeout(() => {
                    searchExternalShows(query);
                }, 180);
            });

            elements.formTitle.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    closeAutocomplete();
                }
            });
        }

        // Autocomplete click delegation
        if (elements.autocompleteDropdown) {
            elements.autocompleteDropdown.addEventListener('click', (e) => {
                const item = e.target.closest('.ac-item');
                if (item && item.dataset.tvmazeId) {
                    selectExternalShow(item.dataset.tvmazeId);
                }
            });
        }

        // Click outside closes autocomplete
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.autocomplete-wrapper')) {
                closeAutocomplete();
            }
        });

        // Detail Modal
        if (elements.btnCloseDetailModal) elements.btnCloseDetailModal.addEventListener('click', closeDetailModal);
        if (elements.btnDetailClose) elements.btnDetailClose.addEventListener('click', closeDetailModal);

        // Delete Modal
        if (elements.btnCloseDeleteModal) elements.btnCloseDeleteModal.addEventListener('click', closeDeleteModal);
        if (elements.btnCancelDelete) elements.btnCancelDelete.addEventListener('click', closeDeleteModal);
        if (elements.btnConfirmDelete) elements.btnConfirmDelete.addEventListener('click', confirmDeleteShow);

        // Popover Triggers Delegation (Clicks on Season Pills)
        document.addEventListener('click', (e) => {
            const seasonBtn = e.target.closest('.season-pill-btn');
            if (seasonBtn) {
                e.stopPropagation();
                const seasonId = seasonBtn.dataset.seasonId;
                const showId = seasonBtn.dataset.showId;
                if (AppState.activePopover && AppState.activePopover.seasonId === Number(seasonId)) {
                    closeSeasonPopover();
                } else {
                    openSeasonPopover(seasonBtn, seasonId, showId);
                }
                return;
            }

            // If click is inside popover, ignore closing
            if (e.target.closest('#season-popover')) {
                return;
            }

            // Click outside popover closes it
            if (AppState.activePopover) {
                closeSeasonPopover();
            }
        });

        // Popover Controls
        if (elements.popoverCloseBtn) elements.popoverCloseBtn.addEventListener('click', closeSeasonPopover);

        if (elements.popoverBtnStepDown) {
            elements.popoverBtnStepDown.addEventListener('click', () => {
                if (!AppState.activePopover) return;
                SpamGuard.guardClick(elements.popoverBtnStepDown, 180);
                const current = AppState.activePopover.season.episodes_watched;
                if (current > 0) {
                    updateSeasonEpisodeCount(AppState.activePopover.seasonId, current - 1);
                }
            });
        }

        if (elements.popoverBtnStepUp) {
            elements.popoverBtnStepUp.addEventListener('click', () => {
                if (!AppState.activePopover) return;
                SpamGuard.guardClick(elements.popoverBtnStepUp, 180);
                const current = AppState.activePopover.season.episodes_watched;
                const total = AppState.activePopover.season.total_episodes;
                if (current < total) {
                    updateSeasonEpisodeCount(AppState.activePopover.seasonId, current + 1);
                }
            });
        }

        if (elements.popoverBtnToggleAll) {
            elements.popoverBtnToggleAll.addEventListener('click', () => {
                if (!AppState.activePopover) return;
                SpamGuard.guardClick(elements.popoverBtnToggleAll, 300);
                toggleSeasonComplete(AppState.activePopover.seasonId);
            });
        }

        if (elements.popoverEpisodesGrid) {
            elements.popoverEpisodesGrid.addEventListener('click', (e) => {
                const chip = e.target.closest('.ep-chip-btn');
                if (chip && AppState.activePopover) {
                    SpamGuard.guardClick(chip, 180);
                    const ep = parseInt(chip.dataset.ep, 10);
                    const current = AppState.activePopover.season.episodes_watched;
                    // If clicking currently active episode chip, toggle back to previous (or 0)
                    const targetEp = (current === ep) ? ep - 1 : ep;
                    updateSeasonEpisodeCount(AppState.activePopover.seasonId, targetEp);
                }
            });
        }

        const resetZeroBtn = document.getElementById('popover-btn-reset-zero');
        if (resetZeroBtn) {
            resetZeroBtn.addEventListener('click', () => {
                if (AppState.activePopover) {
                    SpamGuard.guardClick(resetZeroBtn, 180);
                    updateSeasonEpisodeCount(AppState.activePopover.seasonId, 0);
                }
            });
        }

        // Backup Actions
        if (elements.btnExportJson) elements.btnExportJson.addEventListener('click', exportBackup);
        if (elements.btnImportTrigger) {
            elements.btnImportTrigger.addEventListener('click', () => {
                if (!SpamGuard.acquire('import_trigger', 800)) return;
                if (elements.importFileInput) elements.importFileInput.click();
            });
        }
        if (elements.importFileInput) {
            elements.importFileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    importBackup(e.target.files[0]);
                    e.target.value = '';
                }
            });
        }

        const btnEmailDigest = document.getElementById('btn-email-digest');
        if (btnEmailDigest) {
            btnEmailDigest.addEventListener('click', sendTestEmailDigest);
        }

        // Auth Form Submits (Login & Register page buttons)
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', () => {
                const btn = document.getElementById('btn-login-submit');
                if (btn) Loading.setButtonLoading(btn, true, 'Signing In...');
            });
        }
        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', () => {
                const btn = document.getElementById('btn-register-submit');
                if (btn) Loading.setButtonLoading(btn, true, 'Creating Account...');
            });
        }

        // Google OAuth button handlers
        const googleLoginBtn = document.getElementById('btn-google-login') || document.getElementById('btn-google-register');
        if (googleLoginBtn) {
            googleLoginBtn.addEventListener('click', (e) => {
                if (!SpamGuard.guardClick(googleLoginBtn, 2000)) {
                    e.preventDefault();
                    return;
                }
                Loading.setButtonLoading(googleLoginBtn, true, 'Connecting to Google...');
            });
        }

        // Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (elements.showFormModal && elements.showFormModal.style.display !== 'none') closeFormModal();
                if (elements.showDetailModal && elements.showDetailModal.style.display !== 'none') closeDetailModal();
                if (elements.deleteConfirmModal && elements.deleteConfirmModal.style.display !== 'none') closeDeleteModal();
                if (AppState.activePopover) closeSeasonPopover();
            } else if (e.key === '/' && elements.searchInput && document.activeElement !== elements.searchInput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
                e.preventDefault();
                elements.searchInput.focus();
            }
        });
    }

    // Public API Export for inline handlers
    window.TrackerApp = {
        openDetailModal,
        openEditModal,
        openDeleteModal,
        stepQuickEpisode,
        toggleSeasonComplete,
        reindexSeasonBuilderRows,
        reindexSeasonRows: reindexSeasonBuilderRows,
        Loading,
        Toast,
        SpamGuard,
    };

    // Initialize
    function init() {
        initTheme();
        initData();
        setupEventListeners();
        renderApp();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
