/**
 * Premier League Betting Analysis - Chart.js Factory
 * Requires Chart.js 4.4.1 loaded via CDN
 */

const ChartFactory = {

    // Registry of active chart instances keyed by canvas ID
    _instances: {},

    // Brand palette
    colors: {
        green:  '#00ff85',
        pink:   '#e90052',
        amber:  '#ffc107',
        blue:   '#3b82f6',
        purple: '#8b5cf6',
    },

    // Ordered palette array for datasets
    palette: ['#00ff85', '#e90052', '#ffc107', '#3b82f6', '#8b5cf6'],

    // Default dark-theme overrides applied once on first use
    defaults: {
        font: {
            family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            size: 12,
        },
        gridColor:    'rgba(255, 255, 255, 0.05)',
        tickColor:    '#8892b0',
        tooltipBg:    'rgba(22, 33, 62, 0.95)',
        tooltipBorder:'rgba(255, 255, 255, 0.1)',
        tooltipTitle: '#ffffff',
        tooltipBody:  '#a0a0a0',
        legendColor:  '#8892b0',
    },

    /**
     * Apply global Chart.js defaults for the dark theme.
     * Called automatically on the first chart creation.
     */
    _applyDefaults() {
        if (this._defaultsApplied) return;
        this._defaultsApplied = true;

        const d = this.defaults;

        Chart.defaults.font.family = d.font.family;
        Chart.defaults.font.size   = d.font.size;
        Chart.defaults.color        = d.tickColor;

        Chart.defaults.plugins.tooltip.backgroundColor  = d.tooltipBg;
        Chart.defaults.plugins.tooltip.titleColor        = d.tooltipTitle;
        Chart.defaults.plugins.tooltip.bodyColor         = d.tooltipBody;
        Chart.defaults.plugins.tooltip.borderColor       = d.tooltipBorder;
        Chart.defaults.plugins.tooltip.borderWidth       = 1;
        Chart.defaults.plugins.tooltip.cornerRadius      = 6;
        Chart.defaults.plugins.tooltip.padding           = 10;

        Chart.defaults.plugins.legend.labels.color       = d.legendColor;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.pointStyle  = 'circle';

        Chart.defaults.scale.grid.color                  = d.gridColor;
        Chart.defaults.scale.ticks.color                 = d.tickColor;
    },

    // ------------------------------------------------------------------
    //  Helpers
    // ------------------------------------------------------------------

    /**
     * Destroy any existing chart on the given canvas before creating a new one.
     * @param {string} canvasId
     */
    destroyIfExists(canvasId) {
        if (this._instances[canvasId]) {
            this._instances[canvasId].destroy();
            delete this._instances[canvasId];
        }
    },

    /**
     * Return a canvas 2D context, creating it if the element exists.
     * @param {string} canvasId
     * @returns {CanvasRenderingContext2D|null}
     */
    _getCtx(canvasId) {
        const el = document.getElementById(canvasId);
        if (!el) {
            console.warn(`[ChartFactory] Canvas #${canvasId} not found`);
            return null;
        }
        return el.getContext('2d');
    },

    /**
     * Build common scale options for cartesian charts.
     */
    _cartesianScales(options) {
        return {
            x: {
                grid:  { color: this.defaults.gridColor },
                ticks: { color: this.defaults.tickColor },
                ...(options.scalesX || {}),
            },
            y: {
                grid:  { color: this.defaults.gridColor },
                ticks: { color: this.defaults.tickColor },
                beginAtZero: true,
                ...(options.scalesY || {}),
            },
        };
    },

    // ------------------------------------------------------------------
    //  Chart creators
    // ------------------------------------------------------------------

    /**
     * Create a line chart (accuracy over time, P&L, form trends).
     *
     * @param {string}   canvasId  - ID of the <canvas> element
     * @param {string[]} labels    - X-axis labels
     * @param {Array}    datasets  - Array of { label, data, color? } objects
     * @param {object}   options   - Extra Chart.js options (merged)
     * @returns {Chart|null}
     */
    createLineChart(canvasId, labels, datasets, options = {}) {
        this._applyDefaults();
        this.destroyIfExists(canvasId);

        const ctx = this._getCtx(canvasId);
        if (!ctx) return null;

        const chartDatasets = datasets.map((ds, i) => ({
            label:             ds.label || `Series ${i + 1}`,
            data:              ds.data,
            borderColor:       ds.color || this.palette[i % this.palette.length],
            backgroundColor:   (ds.color || this.palette[i % this.palette.length]) + '1A',
            borderWidth:       2,
            pointRadius:       3,
            pointHoverRadius:  6,
            pointBackgroundColor: ds.color || this.palette[i % this.palette.length],
            tension:           0.3,
            fill:              ds.fill !== undefined ? ds.fill : true,
            ...ds.extra,
        }));

        const chart = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets: chartDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: datasets.length > 1 },
                    ...(options.plugins || {}),
                },
                scales: this._cartesianScales(options),
                ...(options.chartOptions || {}),
            },
        });

        this._instances[canvasId] = chart;
        return chart;
    },

    /**
     * Create a bar chart (H2H comparison, goals breakdown).
     *
     * @param {string}   canvasId
     * @param {string[]} labels
     * @param {Array}    datasets  - Array of { label, data, color? }
     * @param {object}   options
     * @returns {Chart|null}
     */
    createBarChart(canvasId, labels, datasets, options = {}) {
        this._applyDefaults();
        this.destroyIfExists(canvasId);

        const ctx = this._getCtx(canvasId);
        if (!ctx) return null;

        const chartDatasets = datasets.map((ds, i) => ({
            label:           ds.label || `Series ${i + 1}`,
            data:            ds.data,
            backgroundColor: ds.color || this.palette[i % this.palette.length],
            borderColor:     ds.borderColor || 'transparent',
            borderWidth:     ds.borderWidth || 0,
            borderRadius:    4,
            maxBarThickness: 40,
            ...ds.extra,
        }));

        const chart = new Chart(ctx, {
            type: 'bar',
            data: { labels, datasets: chartDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: datasets.length > 1 },
                    ...(options.plugins || {}),
                },
                scales: this._cartesianScales(options),
                ...(options.chartOptions || {}),
            },
        });

        this._instances[canvasId] = chart;
        return chart;
    },

    /**
     * Create a doughnut chart (win/draw/loss distribution, ROI by market).
     *
     * @param {string}   canvasId
     * @param {string[]} labels
     * @param {number[]} data
     * @param {string[]} colors   - One colour per segment
     * @param {object}   options
     * @returns {Chart|null}
     */
    createDoughnutChart(canvasId, labels, data, colors, options = {}) {
        this._applyDefaults();
        this.destroyIfExists(canvasId);

        const ctx = this._getCtx(canvasId);
        if (!ctx) return null;

        const segmentColors = colors || this.palette.slice(0, data.length);

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: segmentColors,
                    borderColor: 'rgba(22, 33, 62, 1)',
                    borderWidth: 2,
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 16,
                            color: this.defaults.legendColor,
                        },
                    },
                    ...(options.plugins || {}),
                },
                ...(options.chartOptions || {}),
            },
        });

        this._instances[canvasId] = chart;
        return chart;
    },

    /**
     * Create a radar chart (team comparison across multiple axes).
     *
     * @param {string}   canvasId
     * @param {string[]} labels    - Axis labels (e.g. Attack, Defence, Form...)
     * @param {Array}    datasets  - Array of { label, data, color? }
     * @param {object}   options
     * @returns {Chart|null}
     */
    createRadarChart(canvasId, labels, datasets, options = {}) {
        this._applyDefaults();
        this.destroyIfExists(canvasId);

        const ctx = this._getCtx(canvasId);
        if (!ctx) return null;

        const chartDatasets = datasets.map((ds, i) => ({
            label:           ds.label || `Team ${i + 1}`,
            data:            ds.data,
            borderColor:     ds.color || this.palette[i % this.palette.length],
            backgroundColor: (ds.color || this.palette[i % this.palette.length]) + '33',
            borderWidth:     2,
            pointRadius:     3,
            pointBackgroundColor: ds.color || this.palette[i % this.palette.length],
            ...ds.extra,
        }));

        const chart = new Chart(ctx, {
            type: 'radar',
            data: { labels, datasets: chartDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        grid:       { color: this.defaults.gridColor },
                        angleLines: { color: this.defaults.gridColor },
                        ticks:      { color: this.defaults.tickColor, backdropColor: 'transparent' },
                        pointLabels:{ color: this.defaults.tickColor, font: { size: 12 } },
                        beginAtZero: true,
                        ...(options.scalesR || {}),
                    },
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: this.defaults.legendColor },
                    },
                    ...(options.plugins || {}),
                },
                ...(options.chartOptions || {}),
            },
        });

        this._instances[canvasId] = chart;
        return chart;
    },

    // ------------------------------------------------------------------
    //  Utilities
    // ------------------------------------------------------------------

    /**
     * Get an existing chart instance by canvas ID.
     * @param {string} canvasId
     * @returns {Chart|undefined}
     */
    get(canvasId) {
        return this._instances[canvasId];
    },

    /**
     * Destroy all tracked chart instances.
     */
    destroyAll() {
        Object.keys(this._instances).forEach(id => this.destroyIfExists(id));
    },

    /**
     * Update data on an existing chart without recreating it.
     * @param {string}   canvasId
     * @param {string[]} labels
     * @param {Array}    datasets  - Same shape as creation datasets
     */
    updateChart(canvasId, labels, datasets) {
        const chart = this._instances[canvasId];
        if (!chart) return;

        chart.data.labels = labels;
        datasets.forEach((ds, i) => {
            if (chart.data.datasets[i]) {
                chart.data.datasets[i].data = ds.data;
                if (ds.label) chart.data.datasets[i].label = ds.label;
            }
        });
        chart.update();
    },
};
