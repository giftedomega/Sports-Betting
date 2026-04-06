/**
 * Premier League Betting Analysis - Reusable UI Components
 */

const Components = {

    // ------------------------------------------------------------------
    //  Animated counter
    // ------------------------------------------------------------------

    /**
     * Animate a number counting up from 0 to target.
     *
     * @param {HTMLElement} element   - DOM element whose textContent will be updated
     * @param {number}      target    - Final numeric value
     * @param {number}      duration  - Animation length in ms (default 1000)
     * @param {string}      prefix    - Text before the number (e.g. "$")
     * @param {string}      suffix    - Text after the number (e.g. "%")
     */
    animateCounter(element, target, duration = 1000, prefix = '', suffix = '') {
        if (!element) return;

        const start = performance.now();
        const isFloat = !Number.isInteger(target);

        function tick(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out quad
            const eased = 1 - (1 - progress) * (1 - progress);
            const current = eased * target;

            element.textContent = prefix + (isFloat ? current.toFixed(1) : Math.round(current)) + suffix;

            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        }

        requestAnimationFrame(tick);
    },

    // ------------------------------------------------------------------
    //  Gauge rings
    // ------------------------------------------------------------------

    /**
     * Initialise all gauge elements on the page.
     * Each gauge element should have:
     *   data-value  - 0-100 numeric value
     *   data-color  - (optional) override colour, defaults to --secondary-color
     *
     * Sets a conic-gradient background and injects the value label.
     */
    initGauges() {
        document.querySelectorAll('[data-gauge]').forEach(el => {
            const value = parseFloat(el.dataset.value) || 0;
            const color = el.dataset.color || '#00ff85';
            const trackColor = 'rgba(255, 255, 255, 0.05)';

            const angle = (value / 100) * 360;
            el.style.background = `conic-gradient(${color} ${angle}deg, ${trackColor} ${angle}deg)`;
            el.style.borderRadius = '50%';
            el.style.display = 'flex';
            el.style.alignItems = 'center';
            el.style.justifyContent = 'center';
            el.style.position = 'relative';

            // Inner circle to create doughnut shape
            if (!el.querySelector('.gauge-inner')) {
                const inner = document.createElement('div');
                inner.className = 'gauge-inner';
                Object.assign(inner.style, {
                    width: '75%',
                    height: '75%',
                    borderRadius: '50%',
                    background: 'var(--bg-card, #16213e)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 'bold',
                    fontSize: '1.25rem',
                });
                inner.textContent = `${Math.round(value)}%`;
                el.appendChild(inner);
            }
        });
    },

    // ------------------------------------------------------------------
    //  Tabs
    // ------------------------------------------------------------------

    /**
     * Initialise tab switching within a container.
     * Expected markup:
     *   <div class="tabs" data-tabs>
     *     <button class="tab-btn active" data-tab="tab1">Label</button>
     *   </div>
     *   <div class="tab-panel active" id="tab1">...</div>
     *
     * @param {string} containerSelector - CSS selector for the parent container
     */
    initTabs(containerSelector) {
        const container = document.querySelector(containerSelector);
        if (!container) return;

        const buttons = container.querySelectorAll('[data-tab]');
        const panels  = container.querySelectorAll('.tab-panel');

        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.dataset.tab;

                buttons.forEach(b => b.classList.remove('active'));
                panels.forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                const panel = container.querySelector(`#${target}`);
                if (panel) panel.classList.add('active');
            });
        });
    },

    // ------------------------------------------------------------------
    //  Toast notifications
    // ------------------------------------------------------------------

    /** @type {HTMLElement|null} */
    _toastContainer: null,

    /**
     * Show a toast notification.
     *
     * @param {string} message  - Display text
     * @param {string} type     - 'info' | 'success' | 'warning' | 'error'
     * @param {number} duration - Time in ms before auto-dismiss (default 3000)
     */
    showToast(message, type = 'info', duration = 3000) {
        // Ensure container exists
        if (!this._toastContainer) {
            this._toastContainer = document.createElement('div');
            Object.assign(this._toastContainer.style, {
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                zIndex: '9999',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                pointerEvents: 'none',
            });
            document.body.appendChild(this._toastContainer);
        }

        const colorMap = {
            info:    { bg: '#37003c',  text: '#ffffff' },
            success: { bg: '#00ff85',  text: '#37003c' },
            warning: { bg: '#ffc107',  text: '#1a1a2e' },
            error:   { bg: '#e90052',  text: '#ffffff' },
        };
        const scheme = colorMap[type] || colorMap.info;

        const toast = document.createElement('div');
        toast.textContent = message;
        Object.assign(toast.style, {
            padding: '12px 24px',
            borderRadius: '8px',
            backgroundColor: scheme.bg,
            color: scheme.text,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            fontSize: '0.875rem',
            fontWeight: '500',
            pointerEvents: 'auto',
            opacity: '0',
            transform: 'translateX(40px)',
            transition: 'opacity 0.3s, transform 0.3s',
        });

        this._toastContainer.appendChild(toast);

        // Trigger enter animation
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });

        // Auto-remove
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(40px)';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    // ------------------------------------------------------------------
    //  Filter pills
    // ------------------------------------------------------------------

    /**
     * Initialise a filter bar with pill-style buttons.
     * Toggles .active on click and calls the callback with the list of
     * currently-active filter values.
     *
     * Expected markup:
     *   <div id="myFilters">
     *     <button class="btn btn-secondary active" data-filter="all">All</button>
     *     <button class="btn btn-secondary" data-filter="low">Low Risk</button>
     *   </div>
     *
     * @param {string}   containerId - ID of the filter container
     * @param {function} callback    - Receives array of active filter values
     */
    initFilters(containerId, callback) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const buttons = container.querySelectorAll('[data-filter]');

        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const value = btn.dataset.filter;

                // "all" is mutually exclusive with other filters
                if (value === 'all') {
                    buttons.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                } else {
                    // Deactivate "all" if another filter is picked
                    container.querySelector('[data-filter="all"]')?.classList.remove('active');
                    btn.classList.toggle('active');

                    // If nothing is active, re-activate "all"
                    const anyActive = container.querySelector('[data-filter].active');
                    if (!anyActive) {
                        container.querySelector('[data-filter="all"]')?.classList.add('active');
                    }
                }

                const activeFilters = Array.from(container.querySelectorAll('[data-filter].active'))
                    .map(b => b.dataset.filter);

                if (typeof callback === 'function') {
                    callback(activeFilters);
                }
            });
        });
    },

    // ------------------------------------------------------------------
    //  Formatting helpers
    // ------------------------------------------------------------------

    /**
     * Format a date string to "6 Apr 2026, 15:00".
     *
     * @param {string} dateString - ISO date string or parseable date
     * @returns {string}
     */
    formatDate(dateString) {
        if (!dateString) return 'TBD';
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'TBD';

        const day     = date.getDate();
        const month   = date.toLocaleString('en-GB', { month: 'short' });
        const year    = date.getFullYear();
        const hours   = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');

        return `${day} ${month} ${year}, ${hours}:${minutes}`;
    },

    /**
     * Map an outcome code to a human-readable label.
     *
     * @param {string} outcome - 'home_win', 'away_win', or 'draw'
     * @returns {string}
     */
    formatOutcome(outcome) {
        const map = {
            home_win: 'Home Win',
            away_win: 'Away Win',
            draw:     'Draw',
        };
        return map[outcome] || outcome || 'Unknown';
    },

    /**
     * Create form dots HTML from a form string like "WWDLW".
     * Each character becomes a coloured badge.
     *
     * @param {string} formString
     * @returns {string} HTML string
     */
    createFormDots(formString) {
        if (!formString) return '<span class="text-secondary">-</span>';

        return formString.split('').map(r => {
            const cls = r === 'W' ? 'win' : r === 'D' ? 'draw' : 'loss';
            return `<span class="form-result ${cls}">${r}</span>`;
        }).join('');
    },

    /**
     * Create a weather widget HTML snippet.
     *
     * @param {object} data - { temperature, description, wind_speed, humidity, icon }
     * @returns {string} HTML string
     */
    createWeatherWidget(data) {
        if (!data) return '';

        const icon = data.icon || '';
        const desc = data.description || '';
        const temp = data.temperature != null ? `${data.temperature}°C` : '-';
        const wind = data.wind_speed != null ? `${data.wind_speed} km/h` : '-';
        const hum  = data.humidity != null ? `${data.humidity}%` : '-';

        return `
            <div class="weather-widget card">
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                    ${icon ? `<span style="font-size:2rem;">${icon}</span>` : ''}
                    <div>
                        <div style="font-size:1.5rem;font-weight:bold;">${temp}</div>
                        <div style="color:var(--text-secondary);font-size:0.875rem;">${desc}</div>
                    </div>
                </div>
                <div style="display:flex;gap:1.5rem;font-size:0.875rem;color:var(--text-secondary);">
                    <span>Wind: ${wind}</span>
                    <span>Humidity: ${hum}</span>
                </div>
            </div>
        `;
    },
};
