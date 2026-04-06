/**
 * Premier League Betting Analysis v2.0 - Core Application JavaScript
 */

// WebSocket state
let ws = null;
let wsConnected = false;
let wsReconnectDelay = 1000;
const WS_MAX_DELAY = 30000;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    initWebSocket();
    initHTMX();
    updateConnectionStatus();

    // Initialize Lucide icons
    if (window.lucide) lucide.createIcons();
});

/**
 * WebSocket connection with auto-reconnect
 */
function initWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            wsConnected = true;
            wsReconnectDelay = 1000;
            updateConnectionStatus();
            console.log('[WS] Connected');
        };

        ws.onclose = () => {
            wsConnected = false;
            updateConnectionStatus();
            console.log('[WS] Disconnected, reconnecting...');
            setTimeout(initWebSocket, wsReconnectDelay);
            wsReconnectDelay = Math.min(wsReconnectDelay * 1.5, WS_MAX_DELAY);
        };

        ws.onerror = (err) => {
            wsConnected = false;
            updateConnectionStatus();
            console.error('[WS] Error:', err);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                // Non-JSON message, ignore
            }
        };
    } catch (e) {
        console.error('[WS] Failed to connect:', e);
        setTimeout(initWebSocket, wsReconnectDelay);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(data) {
    if (data.type === 'background_update') {
        // Update last update timestamp
        const el = document.getElementById('last-update');
        if (el) {
            const time = new Date(data.timestamp).toLocaleTimeString('en-GB');
            el.textContent = `Last update: ${time}`;
        }

        // Show toast
        if (typeof Components !== 'undefined' && Components.showToast) {
            const status = data.status === 'completed' ? 'success' : 'error';
            Components.showToast(`${data.task} ${data.status}`, status);
        }

        // Trigger HTMX refresh for relevant sections
        const refreshMap = {
            'fixtures': ['#fixtures-list', '#fixtures-container'],
            'team_stats': ['#league-table', '#league-table-container'],
            'news': ['#news-feed'],
            'odds': ['#odds-container'],
            'injuries': [],
            'weather': [],
            'intelligence': ['#insights-feed'],
        };

        const targets = refreshMap[data.task] || [];
        targets.forEach(selector => {
            const el = document.querySelector(selector);
            if (el && window.htmx) htmx.trigger(el, 'refresh');
        });
    }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus() {
    const dot = document.getElementById('connection-dot');
    const text = document.getElementById('connection-text');

    if (dot) {
        dot.className = wsConnected ? 'connection-dot connected' : 'connection-dot disconnected';
    }
    if (text) {
        text.textContent = wsConnected ? 'Live' : 'Offline';
    }
}

/**
 * HTMX global configuration
 */
function initHTMX() {
    // Add global headers
    document.body.addEventListener('htmx:configRequest', (event) => {
        event.detail.headers['X-Requested-With'] = 'XMLHttpRequest';
    });

    // Handle errors
    document.body.addEventListener('htmx:responseError', (event) => {
        console.error('[HTMX] Error:', event.detail);
        if (typeof Components !== 'undefined') {
            Components.showToast('Request failed', 'error');
        }
    });

    // After any swap, re-init dynamic components
    document.body.addEventListener('htmx:afterSwap', () => {
        if (window.lucide) lucide.createIcons();
        if (typeof Components !== 'undefined') {
            Components.initGauges();
        }
    });
}
