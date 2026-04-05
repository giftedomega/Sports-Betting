/**
 * Premier League Betting Analysis - Frontend JavaScript
 */

// WebSocket connection status
let wsConnected = false;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    updateConnectionStatus();
});

/**
 * Initialize WebSocket connection handling
 */
function initWebSocket() {
    // HTMX WebSocket events
    document.body.addEventListener('htmx:wsOpen', function(event) {
        wsConnected = true;
        updateConnectionStatus();
        console.log('WebSocket connected');
    });

    document.body.addEventListener('htmx:wsClose', function(event) {
        wsConnected = false;
        updateConnectionStatus();
        console.log('WebSocket disconnected');
    });

    document.body.addEventListener('htmx:wsError', function(event) {
        wsConnected = false;
        updateConnectionStatus();
        console.error('WebSocket error:', event.detail);
    });

    // Handle incoming WebSocket messages
    document.body.addEventListener('htmx:wsAfterMessage', function(event) {
        try {
            const data = JSON.parse(event.detail.message);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    });
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(data) {
    if (data.type === 'background_update') {
        // Update last update timestamp
        const timestamp = new Date(data.timestamp).toLocaleTimeString();
        document.getElementById('global-last-update').textContent = timestamp;

        // Show notification
        showNotification(`${data.task} updated`, data.status);

        // Optionally refresh affected sections
        if (data.task === 'fixtures') {
            const fixturesList = document.getElementById('fixtures-list');
            if (fixturesList) {
                htmx.trigger(fixturesList, 'refresh');
            }
        } else if (data.task === 'team_stats') {
            const leagueTable = document.getElementById('league-table');
            if (leagueTable) {
                htmx.trigger(leagueTable, 'refresh');
            }
        } else if (data.task === 'news') {
            const newsFeed = document.getElementById('news-feed');
            if (newsFeed) {
                htmx.trigger(newsFeed, 'refresh');
            }
        }
    }
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus() {
    const statusDot = document.getElementById('connection-status');
    const lastUpdate = document.getElementById('last-update');

    if (statusDot) {
        if (wsConnected) {
            statusDot.classList.remove('disconnected');
            statusDot.title = 'Connected';
        } else {
            statusDot.classList.add('disconnected');
            statusDot.title = 'Disconnected';
        }
    }

    if (lastUpdate) {
        lastUpdate.textContent = wsConnected ? 'Connected' : 'Disconnected';
    }
}

/**
 * Show a notification toast
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        padding: '12px 24px',
        borderRadius: '8px',
        backgroundColor: type === 'completed' ? '#00ff85' : type === 'error' ? '#e90052' : '#37003c',
        color: type === 'completed' ? '#37003c' : '#ffffff',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        zIndex: '9999',
        animation: 'slideIn 0.3s ease-out'
    });

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'TBD';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format match outcome for display
 */
function formatOutcome(outcome) {
    const map = {
        'home_win': 'Home Win',
        'away_win': 'Away Win',
        'draw': 'Draw'
    };
    return map[outcome] || outcome || 'Unknown';
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Global HTMX configuration
document.body.addEventListener('htmx:configRequest', function(event) {
    // Add any global headers here
    event.detail.headers['X-Requested-With'] = 'XMLHttpRequest';
});

// Handle HTMX errors
document.body.addEventListener('htmx:responseError', function(event) {
    console.error('HTMX response error:', event.detail);
    showNotification('Request failed', 'error');
});
