/**
 * Premier League Betting Analysis - Data Formatters
 * Converts JSON API responses into HTML strings using CSS classes from styles.css.
 * Uses Components for helper functions (formatOutcome, createFormDots, formatDate).
 */

const Formatters = {

    // ------------------------------------------------------------------
    //  Fixtures
    // ------------------------------------------------------------------

    /**
     * Format a list of fixtures into compact HTML cards (dashboard widget).
     *
     * @param {Array} fixtures
     * @returns {string} HTML
     */
    formatFixtures(fixtures) {
        if (!fixtures || fixtures.length === 0) {
            return '<p class="empty">No upcoming fixtures</p>';
        }

        return fixtures.map(f => `
            <div class="fixture-card">
                <div class="fixture-teams">
                    <span class="team home">${f.home_team}</span>
                    <span class="vs">vs</span>
                    <span class="team away">${f.away_team}</span>
                </div>
                <div class="fixture-meta">
                    ${Components.formatDate(f.match_date)}
                    ${f.round ? ' | GW' + f.round : (f.gameweek ? ' | GW' + f.gameweek : '')}
                    ${f.status && f.status !== 'scheduled' ? ' <span class="badge badge-' + f.status + '">(' + f.status + ')</span>' : ''}
                </div>
            </div>
        `).join('');
    },

    // ------------------------------------------------------------------
    //  League table (compact - dashboard)
    // ------------------------------------------------------------------

    /**
     * Format a compact league table (top N rows).
     *
     * @param {Array}  teams
     * @param {number|null} limit - Number of rows to show (null = 10)
     * @returns {string} HTML
     */
    formatLeagueTable(teams, limit = null) {
        if (!teams || teams.length === 0) {
            return '<p class="empty">No data available</p>';
        }

        const rows = limit ? teams.slice(0, limit) : teams.slice(0, 10);

        return `
            <table class="league-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Team</th>
                        <th>P</th>
                        <th>W</th>
                        <th>D</th>
                        <th>L</th>
                        <th>GD</th>
                        <th>Pts</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(t => {
                        const gd = (t.goals_for || 0) - (t.goals_against || 0);
                        return `
                        <tr>
                            <td>${t.position || '-'}</td>
                            <td>${t.name}</td>
                            <td>${t.played || 0}</td>
                            <td>${t.won || 0}</td>
                            <td>${t.drawn || 0}</td>
                            <td>${t.lost || 0}</td>
                            <td class="${gd > 0 ? 'positive' : gd < 0 ? 'negative' : ''}">${gd > 0 ? '+' + gd : gd}</td>
                            <td><strong>${t.points || 0}</strong></td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
        `;
    },

    // ------------------------------------------------------------------
    //  Full league table (teams page)
    // ------------------------------------------------------------------

    /**
     * Format the full league table with all columns, form, and detail buttons.
     *
     * @param {Array} teams
     * @returns {string} HTML
     */
    formatFullTable(teams) {
        if (!teams || teams.length === 0) {
            return '<p class="empty">No data available</p>';
        }

        return `
            <table class="league-table full">
                <thead>
                    <tr>
                        <th>Pos</th>
                        <th>Team</th>
                        <th>P</th>
                        <th>W</th>
                        <th>D</th>
                        <th>L</th>
                        <th>GF</th>
                        <th>GA</th>
                        <th>GD</th>
                        <th>Pts</th>
                        <th>Form</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    ${teams.map((t, i) => {
                        const pos = t.position || i + 1;
                        const gd = (t.goals_for || 0) - (t.goals_against || 0);
                        const gdStr = gd > 0 ? '+' + gd : String(gd);
                        const gdCls = gd > 0 ? 'positive' : gd < 0 ? 'negative' : '';
                        const rowCls = Formatters._positionClass(pos);

                        return `
                        <tr class="${rowCls}">
                            <td>${pos}</td>
                            <td class="team-name">${t.name}</td>
                            <td>${t.played || 0}</td>
                            <td>${t.won || 0}</td>
                            <td>${t.drawn || 0}</td>
                            <td>${t.lost || 0}</td>
                            <td>${t.goals_for || 0}</td>
                            <td>${t.goals_against || 0}</td>
                            <td class="${gdCls}">${gdStr}</td>
                            <td><strong>${t.points || 0}</strong></td>
                            <td class="form">${Components.createFormDots(t.form)}</td>
                            <td>
                                <button class="btn btn-small" hx-get="/api/teams/${encodeURIComponent(t.name)}" hx-target="#team-detail" hx-swap="innerHTML">
                                    Details
                                </button>
                            </td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
            <div id="team-detail" class="team-detail-panel"></div>
        `;
    },

    // ------------------------------------------------------------------
    //  News
    // ------------------------------------------------------------------

    /**
     * Format news articles into a feed list.
     *
     * @param {Array}  articles
     * @param {number} limit - Max articles to show (default 5)
     * @returns {string} HTML
     */
    formatNews(articles, limit = 5) {
        if (!articles || articles.length === 0) {
            return '<p class="empty">No news available</p>';
        }

        return articles.slice(0, limit).map(a => `
            <div class="news-item ${a.impact || ''}">
                <a href="${a.url || '#'}" target="_blank" rel="noopener">${a.title}</a>
                <div class="news-meta">
                    <span class="source">${a.source || ''}</span>
                    ${a.published_at ? `<span class="date">${Components.formatDate(a.published_at)}</span>` : ''}
                    ${a.sentiment ? `<span class="sentiment ${a.sentiment}">${a.sentiment}</span>` : ''}
                </div>
            </div>
        `).join('');
    },

    // ------------------------------------------------------------------
    //  Predictions (compact - dashboard)
    // ------------------------------------------------------------------

    /**
     * Format predictions into compact cards.
     *
     * @param {Array} predictions
     * @returns {string} HTML
     */
    formatPredictions(predictions) {
        if (!predictions || predictions.length === 0) {
            return '<p class="empty">No predictions yet. Click "Analyze" to generate.</p>';
        }

        return predictions.map(p => `
            <div class="prediction-card ${p.risk_level || ''}">
                <div class="match">${p.home_team} vs ${p.away_team}</div>
                <div class="prediction">
                    <span class="outcome">${Components.formatOutcome(p.predicted_outcome)}</span>
                    <span class="confidence">${p.confidence || 0}% confidence</span>
                </div>
                <div class="summary">${p.summary || ''}</div>
            </div>
        `).join('');
    },

    // ------------------------------------------------------------------
    //  Prediction stats
    // ------------------------------------------------------------------

    /**
     * Format prediction performance statistics into stat cards.
     *
     * @param {object} stats - { total_predictions, correct_predictions, accuracy, total_profit_loss }
     * @returns {string} HTML
     */
    formatPredictionStats(stats) {
        if (!stats) return '';

        const plValue = stats.total_profit_loss || 0;
        const plClass = plValue >= 0 ? 'positive' : 'negative';
        const plSign  = plValue >= 0 ? '+' : '';

        return `
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-value">${stats.total_predictions || 0}</span>
                    <span class="stat-label">Total Predictions</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${stats.correct_predictions || 0}</span>
                    <span class="stat-label">Correct</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${(stats.accuracy || 0).toFixed(1)}%</span>
                    <span class="stat-label">Accuracy</span>
                </div>
                <div class="stat-card ${plClass}">
                    <span class="stat-value">${plSign}${plValue.toFixed(2)}</span>
                    <span class="stat-label">Profit/Loss</span>
                </div>
            </div>
        `;
    },

    // ------------------------------------------------------------------
    //  System status
    // ------------------------------------------------------------------

    /**
     * Format system status response into a status panel.
     *
     * @param {object} status
     * @returns {string} HTML
     */
    formatStatus(status) {
        if (!status) return '<p class="empty">Status unavailable</p>';

        const statusClass = status.status === 'operational' ? 'success' : 'warning';
        const ollamaStatus = status.ollama?.status || 'unknown';
        const ollamaClass  = ollamaStatus === 'connected' ? 'success' : 'error';

        return `
            <div class="status-info">
                <div class="status-item">
                    <span class="label">Status:</span>
                    <span class="value ${statusClass}">${status.status || 'unknown'}</span>
                </div>
                <div class="status-item">
                    <span class="label">Ollama:</span>
                    <span class="value ${ollamaClass}">${ollamaStatus}</span>
                </div>
                <div class="status-item">
                    <span class="label">Model:</span>
                    <span class="value">${status.config?.model || 'N/A'}</span>
                </div>
                ${status.last_refresh ? `
                <div class="status-item">
                    <span class="label">Last Refresh:</span>
                    <span class="value">${Components.formatDate(status.last_refresh)}</span>
                </div>` : ''}
                ${status.fixtures_count != null ? `
                <div class="status-item">
                    <span class="label">Fixtures Cached:</span>
                    <span class="value">${status.fixtures_count}</span>
                </div>` : ''}
            </div>
        `;
    },

    // ------------------------------------------------------------------
    //  Prediction detail (modal / inline)
    // ------------------------------------------------------------------

    /**
     * Format a single prediction for display in a modal or detail view.
     *
     * @param {object} prediction
     * @returns {string} HTML
     */
    formatPredictionDetail(prediction) {
        if (!prediction) return '';

        const p = prediction;

        return `
            <div class="modal-content">
                <button class="modal-close" onclick="this.parentElement.parentElement.style.display='none'">&times;</button>
                <h2>${p.home_team} vs ${p.away_team}</h2>

                <div class="outcome-display ${p.predicted_outcome || ''}">
                    <span class="label">Predicted Outcome</span>
                    <span class="value">${Components.formatOutcome(p.predicted_outcome)}</span>
                    <span class="confidence">${p.confidence || 0}% confidence</span>
                </div>

                ${p.predicted_score ? `
                    <div class="score-prediction">
                        <span>${p.predicted_score.home || 0}</span>
                        <span> - </span>
                        <span>${p.predicted_score.away || 0}</span>
                    </div>
                ` : ''}

                ${p.key_factors && p.key_factors.length > 0 ? `
                    <div class="key-factors">
                        <h4>Key Factors</h4>
                        <ul>${p.key_factors.map(f => `<li>${f}</li>`).join('')}</ul>
                    </div>
                ` : ''}

                ${p.recommended_bets && p.recommended_bets.length > 0 ? `
                    <div class="recommended-bets">
                        <h4>Recommended Bets</h4>
                        ${p.recommended_bets.map(b => `
                            <div class="bet-recommendation">
                                <div class="bet-header">
                                    <span class="market">${b.market}</span>
                                    <span class="selection">${b.selection}</span>
                                </div>
                                <div class="bet-meta">
                                    <span class="confidence">${b.confidence}% confidence</span>
                                    ${b.odds_value ? `<span class="value-indicator ${b.odds_value}">${b.odds_value} value</span>` : ''}
                                </div>
                                ${b.reasoning ? `<p class="reasoning">${b.reasoning}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}

                <div class="risk-indicator ${p.risk_level || 'medium'}">
                    Risk: ${(p.risk_level || 'medium').toUpperCase()}
                </div>

                ${p.summary ? `
                    <div class="summary-section">
                        <h4>Summary</h4>
                        <p>${p.summary}</p>
                    </div>
                ` : ''}
            </div>
        `;
    },

    // ------------------------------------------------------------------
    //  Team detail panel
    // ------------------------------------------------------------------

    /**
     * Format a team detail panel with stats and action buttons.
     *
     * @param {object} team
     * @returns {string} HTML
     */
    formatTeamDetail(team) {
        if (!team) return '';

        const gd = (team.goals_for || 0) - (team.goals_against || 0);
        const gdStr = gd > 0 ? '+' + gd : String(gd);

        return `
            <div class="team-detail-content">
                <h3>${team.name}</h3>

                <div class="stats-grid" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr));margin:1rem 0;">
                    <div class="stat-card">
                        <span class="stat-value">${team.position || '-'}</span>
                        <span class="stat-label">Position</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.points || 0}</span>
                        <span class="stat-label">Points</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.played || 0}</span>
                        <span class="stat-label">Played</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.won || 0}</span>
                        <span class="stat-label">Won</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.drawn || 0}</span>
                        <span class="stat-label">Drawn</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.lost || 0}</span>
                        <span class="stat-label">Lost</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.goals_for || 0}</span>
                        <span class="stat-label">Goals For</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${team.goals_against || 0}</span>
                        <span class="stat-label">Goals Against</span>
                    </div>
                    <div class="stat-card ${gd > 0 ? 'positive' : gd < 0 ? 'negative' : ''}">
                        <span class="stat-value">${gdStr}</span>
                        <span class="stat-label">Goal Difference</span>
                    </div>
                </div>

                ${team.form ? `
                    <div style="margin:1rem 0;">
                        <strong>Form:</strong> ${Components.createFormDots(team.form)}
                    </div>
                ` : ''}

                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:1rem;">
                    <button class="btn btn-secondary btn-small" hx-get="/api/teams/${encodeURIComponent(team.name)}/players" hx-target="#team-players-${Formatters._slugify(team.name)}" hx-swap="innerHTML">
                        View Squad
                    </button>
                    <button class="btn btn-secondary btn-small" hx-get="/api/teams/${encodeURIComponent(team.name)}/news" hx-target="#team-news-${Formatters._slugify(team.name)}" hx-swap="innerHTML">
                        Team News
                    </button>
                </div>
                <div id="team-players-${Formatters._slugify(team.name)}"></div>
                <div id="team-news-${Formatters._slugify(team.name)}"></div>
            </div>
        `;
    },

    // ------------------------------------------------------------------
    //  Insights
    // ------------------------------------------------------------------

    /**
     * Format a list of insight objects into HTML.
     *
     * @param {Array} insights - [{ title, description, type, confidence }]
     * @returns {string} HTML
     */
    formatInsights(insights) {
        if (!insights || insights.length === 0) {
            return '<p class="empty">No insights available</p>';
        }

        return `
            <div class="insights-list">
                ${insights.map(ins => {
                    const typeColor = ins.type === 'positive' ? 'success'
                                    : ins.type === 'negative' ? 'danger'
                                    : ins.type === 'warning'  ? 'warning'
                                    : 'info';
                    return `
                    <div class="news-item ${ins.type || ''}">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong>${ins.title}</strong>
                            ${ins.confidence ? `<span class="confidence-badge" style="font-size:0.75rem;">${ins.confidence}%</span>` : ''}
                        </div>
                        <p style="color:var(--text-secondary);font-size:0.875rem;margin-top:0.25rem;">${ins.description || ''}</p>
                    </div>`;
                }).join('')}
            </div>
        `;
    },

    // ------------------------------------------------------------------
    //  Betting summary
    // ------------------------------------------------------------------

    /**
     * Format a betting summary panel with key metrics.
     *
     * @param {object} summary - { total_bets, total_staked, total_returns, profit_loss, roi, win_rate, avg_odds }
     * @returns {string} HTML
     */
    formatBettingSummary(summary) {
        if (!summary) return '<p class="empty">No betting data available</p>';

        const pl      = summary.profit_loss || 0;
        const plSign  = pl >= 0 ? '+' : '';
        const plClass = pl >= 0 ? 'positive' : 'negative';
        const roi     = summary.roi || 0;
        const roiSign = roi >= 0 ? '+' : '';

        return `
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-value">${summary.total_bets || 0}</span>
                    <span class="stat-label">Total Bets</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${(summary.total_staked || 0).toFixed(2)}</span>
                    <span class="stat-label">Total Staked</span>
                </div>
                <div class="stat-card ${plClass}">
                    <span class="stat-value">${plSign}${pl.toFixed(2)}</span>
                    <span class="stat-label">Profit / Loss</span>
                </div>
                <div class="stat-card ${plClass}">
                    <span class="stat-value">${roiSign}${roi.toFixed(1)}%</span>
                    <span class="stat-label">ROI</span>
                </div>
            </div>
            <div class="stats-grid" style="grid-template-columns:repeat(3,1fr);margin-top:1rem;">
                <div class="stat-card">
                    <span class="stat-value">${(summary.win_rate || 0).toFixed(1)}%</span>
                    <span class="stat-label">Win Rate</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${(summary.avg_odds || 0).toFixed(2)}</span>
                    <span class="stat-label">Avg Odds</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${(summary.total_returns || 0).toFixed(2)}</span>
                    <span class="stat-label">Total Returns</span>
                </div>
            </div>
        `;
    },

    // ------------------------------------------------------------------
    //  Bets table
    // ------------------------------------------------------------------

    /**
     * Format tracked bets into an HTML table.
     *
     * @param {Array} bets - [{ date, match, market, selection, odds, stake, result, returns }]
     * @returns {string} HTML
     */
    formatBetsTable(bets) {
        if (!bets || bets.length === 0) {
            return '<p class="empty">No tracked bets</p>';
        }

        return `
            <table class="league-table bets-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Match</th>
                        <th>Market</th>
                        <th>Selection</th>
                        <th>Odds</th>
                        <th>Stake</th>
                        <th>Result</th>
                        <th>Returns</th>
                    </tr>
                </thead>
                <tbody>
                    ${bets.map(b => {
                        const resultCls = b.result === 'won'  ? 'positive'
                                        : b.result === 'lost' ? 'negative'
                                        : '';
                        const returnVal = b.returns != null ? b.returns.toFixed(2) : '-';
                        return `
                        <tr>
                            <td>${Components.formatDate(b.date)}</td>
                            <td>${b.match || `${b.home_team || ''} vs ${b.away_team || ''}`}</td>
                            <td>${b.market || '-'}</td>
                            <td>${b.selection || '-'}</td>
                            <td>${b.odds != null ? b.odds.toFixed(2) : '-'}</td>
                            <td>${b.stake != null ? b.stake.toFixed(2) : '-'}</td>
                            <td class="${resultCls}" style="font-weight:600;text-transform:uppercase;">${b.result || 'pending'}</td>
                            <td class="${resultCls}">${returnVal}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
        `;
    },

    // ------------------------------------------------------------------
    //  Odds display
    // ------------------------------------------------------------------

    /**
     * Format odds for a fixture into a compact display.
     *
     * @param {object} fixture - fixture object with odds property { home_win, draw, away_win, ... }
     * @returns {string} HTML
     */
    formatOdds(fixture) {
        if (!fixture || !fixture.odds) {
            return '<p class="empty" style="font-size:0.875rem;">No odds available</p>';
        }

        const o = fixture.odds;

        let html = `
            <div class="odds-display" style="display:flex;gap:0.5rem;justify-content:center;margin:0.5rem 0;">
                <div class="stat-card" style="padding:0.75rem 1rem;flex:1;text-align:center;">
                    <span class="stat-value" style="font-size:1.25rem;color:#00ff85;">${o.home_win != null ? o.home_win.toFixed(2) : '-'}</span>
                    <span class="stat-label">Home</span>
                </div>
                <div class="stat-card" style="padding:0.75rem 1rem;flex:1;text-align:center;">
                    <span class="stat-value" style="font-size:1.25rem;color:#ffc107;">${o.draw != null ? o.draw.toFixed(2) : '-'}</span>
                    <span class="stat-label">Draw</span>
                </div>
                <div class="stat-card" style="padding:0.75rem 1rem;flex:1;text-align:center;">
                    <span class="stat-value" style="font-size:1.25rem;color:#e90052;">${o.away_win != null ? o.away_win.toFixed(2) : '-'}</span>
                    <span class="stat-label">Away</span>
                </div>
            </div>
        `;

        // Additional markets if present
        const extras = [];
        if (o.over_2_5 != null)  extras.push({ label: 'Over 2.5', value: o.over_2_5 });
        if (o.under_2_5 != null) extras.push({ label: 'Under 2.5', value: o.under_2_5 });
        if (o.btts_yes != null)  extras.push({ label: 'BTTS Yes', value: o.btts_yes });
        if (o.btts_no != null)   extras.push({ label: 'BTTS No', value: o.btts_no });

        if (extras.length > 0) {
            html += `
                <div style="display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;margin-top:0.5rem;">
                    ${extras.map(e => `
                        <div style="background:var(--bg-card);padding:0.5rem 0.75rem;border-radius:var(--border-radius);text-align:center;font-size:0.875rem;">
                            <div style="font-weight:bold;">${e.value.toFixed(2)}</div>
                            <div style="color:var(--text-secondary);font-size:0.75rem;">${e.label}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        return html;
    },

    // ------------------------------------------------------------------
    //  Private helpers
    // ------------------------------------------------------------------

    /**
     * Return a CSS class based on league position.
     * @param {number} pos
     * @returns {string}
     */
    _positionClass(pos) {
        if (pos <= 4)  return 'champions-league';
        if (pos === 5) return 'europa-league';
        if (pos >= 18) return 'relegation';
        return '';
    },

    /**
     * Simple slug helper for generating safe DOM IDs from team names.
     * @param {string} str
     * @returns {string}
     */
    _slugify(str) {
        return (str || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    },
};
