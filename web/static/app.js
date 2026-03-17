/**
 * @typedef {'pending' | 'loading' | 'success' | 'error'} QueryStatus
 */

/**
 * @typedef {object} Query
 * @property {string} id - Unique identifier
 * @property {string} crawler - Crawler name
 * @property {string} username - Username to query
 * @property {QueryStatus} status - Current status
 * @property {number} solved - Number of solved problems
 * @property {number} submissions - Total submissions
 * @property {string[] | null} solvedList - List of solved problem IDs
 * @property {number} duration - Query duration in seconds
 * @property {string | null} error - Error message if failed
 * @property {AbortController | null} abortController - For canceling requests
 */

/**
 * @typedef {object} SavedData
 * @property {string} username - Last used username
 * @property {Array<{crawler: string, username: string}>} queries - Saved queries
 */

/**
 * @typedef {object} HistoryEntry
 * @property {string} date - ISO date string
 * @property {number} totalSolved
 * @property {number} totalSubmissions
 * @property {string} username - Query username
 */

const STORAGE_KEY = 'ojhunt-queries';
const HISTORY_KEY = 'ojhunt-history';
const MAX_HISTORY_ENTRIES = 100;

/**
 * Creates a new Query object with default values
 * @param {string} crawler
 * @param {string} username
 * @param {number} id
 * @returns {Query}
 */
function createQuery(crawler, username, id) {
    return {
        id: String(id),
        crawler,
        username,
        status: 'pending',
        solved: 0,
        submissions: 0,
        solvedList: null,
        duration: 0,
        error: null,
        abortController: null,
    };
}

function ojhunt() {
    return {
        /** @type {Object<string, {title: string, description: string, isVirtualJudge: boolean}>} */
        crawlers: window.__CRAWLERS__,
        
        /** @type {Query[]} */
        queries: [],
        
        /** @type {string} */
        selectedCrawler: '',
        
        /** @type {string} */
        username: '',
        
        /** @type {number} */
        queryIdCounter: 0,
        
        /** @type {{totalSolved: number | null, totalSubmissions: number}} */
        report: {
            totalSolved: null,
            totalSubmissions: 0
        },
        
        /** @type {HistoryEntry[]} */
        history: [],
        
        /** @type {boolean} */
        _initialized: false,
        
        /**
         * Check if a query with given crawler/username already exists
         * @param {string} crawler
         * @param {string} username
         * @returns {boolean}
         */
        queryExists(crawler, username) {
            return this.queries.some(q => q.crawler === crawler && q.username === username);
        },
        
        /**
         * Add a new query (or all crawlers if crawler === '*')
         * @returns {void}
         */
        addQuery() {
            if (!this.selectedCrawler) {
                alert('Please select a crawler');
                return;
            }
            if (!this.username.trim()) {
                alert('Please enter a username');
                return;
            }
            
            const username = this.username.trim();
            
            if (this.selectedCrawler === '*') {
                let added = 0;
                for (const crawlerName of Object.keys(this.crawlers)) {
                    if (!this.queryExists(crawlerName, username)) {
                        this.queries.push(createQuery(crawlerName, username, this.queryIdCounter++));
                        added++;
                    }
                }
                if (added === 0) {
                    alert('All crawlers already added for this username');
                    return;
                }
            } else {
                if (this.queryExists(this.selectedCrawler, username)) {
                    alert('This query already exists in the list');
                    return;
                }
                this.queries.push(createQuery(this.selectedCrawler, username, this.queryIdCounter++));
            }
            
            this.selectedCrawler = '';
            this.saveQueries();
        },
        
        /**
         * Remove a query by ID
         * @param {string} id
         * @returns {void}
         */
        removeQuery(id) {
            const index = this.queries.findIndex(q => q.id === id);
            if (index !== -1) {
                this.queries.splice(index, 1);
                this.saveQueries();
                this.calculateReport();
            }
        },
        
        /**
         * Stop an in-flight query
         * @param {string} id
         * @returns {void}
         */
        stopQuery(id) {
            const q = this.queries.find(q => q.id === id);
            if (q && q.abortController) {
                q.abortController.abort();
            }
        },
        
        /**
         * Execute a single query
         * @param {string} id
         * @returns {Promise<void>}
         */
        async executeQuery(id) {
            const q = this.queries.find(x => x.id === id);
            if (!q) return;
            
            q.status = 'loading';
            q.error = null;
            q.abortController = new AbortController();
            
            try {
                const url = `/api/crawlers/${encodeURIComponent(q.crawler)}/${encodeURIComponent(q.username)}`;
                const response = await fetch(url, { signal: q.abortController.signal });
                const data = await response.json();
                
                if (data.error) {
                    q.status = 'error';
                    q.error = data.message;
                } else {
                    q.status = 'success';
                    q.solved = data.data.solved;
                    q.submissions = data.data.submissions;
                    q.solvedList = data.data.solvedList;
                    q.duration = data.data.duration || 0;
                }
            } catch (e) {
                if (e.name === 'AbortError') {
                    q.status = 'pending';
                    q.error = 'Canceled';
                } else {
                    q.status = 'error';
                    q.error = e.message;
                }
            } finally {
                q.abortController = null;
            }
        },
        
        /**
         * Query a single row
         * @param {string} id
         * @returns {Promise<void>}
         */
        async queryOne(id) {
            await this.executeQuery(id);
            await this.calculateReport();
        },
        
        /**
         * Retry a query
         * @param {string} id
         * @returns {Promise<void>}
         */
        async retryQuery(id) {
            await this.executeQuery(id);
            await this.calculateReport();
        },
        
        /**
         * Query all pending rows
         * @returns {Promise<void>}
         */
        async queryAll() {
            const pendingQueries = this.queries.filter(q => q.status === 'pending' || q.status === 'error');
            if (pendingQueries.length === 0) {
                alert('No pending queries to execute');
                return;
            }
            
            const promises = pendingQueries.map(q => this.executeQuery(q.id));
            await Promise.all(promises);
            await this.calculateReport();
        },
        
        /**
         * Clear all queries
         * @returns {void}
         */
        clearAll() {
            this.queries = [];
            this.report = { totalSolved: null, totalSubmissions: 0 };
            this.saveQueries();
        },
        
        /**
         * Calculate report from successful queries
         * @returns {Promise<void>}
         */
        async calculateReport() {
            const allSolved = new Set();
            let totalSubmissions = 0;
            
            for (const q of this.queries) {
                if (q.status !== 'success') continue;
                
                const isVirtual = this.crawlers[q.crawler]?.isVirtualJudge || false;
                const solvedList = q.solvedList || [];
                
                for (const problem of solvedList) {
                    if (isVirtual) {
                        allSolved.add(problem);
                    } else {
                        allSolved.add(`${q.crawler}-${problem}`);
                    }
                }
                totalSubmissions += q.submissions;
            }
            
            this.report = {
                totalSolved: allSolved.size,
                totalSubmissions
            };
            
            if (allSolved.size > 0) {
                this.saveToHistory();
            }
        },
        
        /**
         * Save current result to history
         * @returns {void}
         */
        saveToHistory() {
            const entry = {
                date: new Date().toISOString(),
                totalSolved: this.report.totalSolved || 0,
                totalSubmissions: this.report.totalSubmissions || 0,
                username: this.username
            };
            
            this.history.push(entry);
            
            if (this.history.length > MAX_HISTORY_ENTRIES) {
                this.history = this.history.slice(-MAX_HISTORY_ENTRIES);
            }
            
            this.saveHistory();
        },
        
        /**
         * Save history to localStorage
         * @returns {void}
         */
        saveHistory() {
            localStorage.setItem(HISTORY_KEY, JSON.stringify(this.history));
        },
        
        /**
         * Load history from localStorage
         * @returns {void}
         */
        loadHistory() {
            const saved = localStorage.getItem(HISTORY_KEY);
            if (!saved) return;
            
            try {
                const data = JSON.parse(saved);
                if (Array.isArray(data)) {
                    this.history = data;
                }
            } catch (e) {}
        },
        
        /**
         * Export all data (queries + history) as JSON
         * @returns {void}
         */
        exportData() {
            const data = {
                version: 1,
                exportedAt: new Date().toISOString(),
                queries: JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'),
                history: this.history
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ojhunt-backup-${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        },
        
        /**
         * Import data from JSON file
         * @param {File} file
         * @returns {Promise<void>}
         */
        async importData(file) {
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                
                if (data.version !== 1) {
                    alert('Unsupported backup version');
                    return;
                }
                
                if (data.queries) {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(data.queries));
                }
                
                if (Array.isArray(data.history)) {
                    this.history = data.history;
                    this.saveHistory();
                }
                
                alert('Data imported successfully. Reloading...');
                location.reload();
            } catch (e) {
                alert('Failed to import data: ' + e.message);
            }
        },
        
        /**
         * Save queries to localStorage
         * @returns {void}
         */
        saveQueries() {
            /** @type {SavedData} */
            const data = {
                username: this.username,
                queries: this.queries.map(q => ({ crawler: q.crawler, username: q.username }))
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        },
        
        /**
         * Load saved queries from localStorage
         * @returns {void}
         */
        loadSavedQueries() {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) return;
            
            try {
                const data = JSON.parse(saved);
                if (data.username) {
                    this.username = data.username;
                }
                if (data.queries && Array.isArray(data.queries)) {
                    data.queries.forEach(q => {
                        if (q.crawler && q.username && this.crawlers[q.crawler]) {
                            this.queries.push(createQuery(q.crawler, q.username, this.queryIdCounter++));
                        }
                    });
                }
            } catch (e) {}
        },
        
        /**
         * Show dialog for solved problems
         * @param {Query} q
         * @returns {void}
         */
        showDialog(q) {
            const dialog = document.getElementById(`dialog-${q.id}`);
            if (dialog) dialog.showModal();
        },
        
        /**
         * Close dialog
         * @param {string} id
         * @returns {void}
         */
        closeDialog(id) {
            const dialog = document.getElementById(`dialog-${id}`);
            if (dialog) dialog.close();
        },
        
        /**
         * Download report as PDF
         * @returns {void}
         */
        downloadReport() {
            const now = new Date();
            const dateStr = now.toISOString().slice(0, 19).replace(/[T:]/g, '-');
            const filename = `ojhunt-report-${dateStr}.pdf`;
            
            const reportContent = this.generateReportHTML();
            const printWindow = window.open('', '_blank');
            if (!printWindow) {
                alert('Please allow popups to download PDF');
                return;
            }
            
            printWindow.document.write(reportContent);
            printWindow.document.close();
            printWindow.focus();
            
            setTimeout(() => {
                printWindow.print();
            }, 250);
        },
        
        /**
         * Generate history chart HTML for PDF
         * @returns {string}
         */
        generateHistoryChartHTML() {
            const data = this.history.slice(-20);
            const maxSolved = Math.max(...data.map(d => d.totalSolved));
            
            let bars = '';
            data.forEach((entry, i) => {
                const height = Math.round((entry.totalSolved / maxSolved) * 100);
                const date = new Date(entry.date).toLocaleDateString();
                bars += `
                    <div class="bar-container">
                        <div class="bar" style="height: ${height}%;">
                            <span class="bar-value">${entry.totalSolved}</span>
                        </div>
                        <span class="bar-label">${date}</span>
                    </div>
                `;
            });
            
            return `
                <div class="history-section">
                    <h2>Progress History</h2>
                    <div class="chart">
                        ${bars}
                    </div>
                </div>
            `;
        },
        
        /**
         * Generate HTML for PDF report
         * @returns {string}
         */
        generateReportHTML() {
            const now = new Date();
            const dateStr = now.toLocaleString();
            const fileDateStr = now.toISOString().slice(0, 19).replace(/[T:]/g, '-');
            
            const successfulQueries = this.queries.filter(q => q.status === 'success');
            const errorQueries = this.queries.filter(q => q.status === 'error');
            
            let tableRows = '';
            for (const q of this.queries) {
                const title = this.crawlers[q.crawler]?.title || q.crawler;
                const statusClass = q.status === 'success' ? 'success' : (q.status === 'error' ? 'error' : '');
                const solved = q.status === 'success' ? q.solved : 'N/A';
                const submissions = q.status === 'success' ? q.submissions : 'N/A';
                const status = q.status === 'success' ? `OK (${q.duration.toFixed(2)}s)` : (q.status === 'error' ? `ERROR: ${q.error}` : q.status);
                
                tableRows += `
                    <tr class="${statusClass}">
                        <td>${title}</td>
                        <td>${q.username}</td>
                        <td>${solved}</td>
                        <td>${submissions}</td>
                        <td>${status}</td>
                    </tr>
                `;
            }
            
            return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OJHunt Report ${fileDateStr}</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; margin-bottom: 0.5rem; }
        .date { text-align: center; color: #666; margin-bottom: 2rem; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
        th, td { padding: 0.5rem; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; font-weight: 600; }
        .success { background: #f0fff4; }
        .error { background: #ffeef0; }
        .summary { background: #e8f5e9; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
        .summary strong { font-size: 1.1rem; }
        .history-section { margin-top: 2rem; }
        .history-section h2 { margin-bottom: 1rem; }
        .chart { display: flex; align-items: flex-end; height: 150px; gap: 4px; }
        .bar-container { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; }
        .bar { background: #4CAF50; width: 100%; border-radius: 2px 2px 0 0; display: flex; align-items: flex-start; justify-content: center; min-height: 20px; }
        .bar-value { color: white; font-size: 10px; padding: 2px; }
        .bar-label { font-size: 8px; color: #666; margin-top: 4px; }
        @media print {
            body { padding: 0; }
            button { display: none; }
        }
    </style>
</head>
<body>
    <h1>OJHunt Lite Report</h1>
    <p class="date">Generated: ${dateStr}</p>
    
    <table>
        <thead>
            <tr>
                <th>Crawler</th>
                <th>Username</th>
                <th>Solved</th>
                <th>Submissions</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            ${tableRows}
        </tbody>
    </table>
    
    <div class="summary">
        <strong>Total: ${this.report.totalSolved || 0} solved / ${this.report.totalSubmissions || 0} submissions</strong>
    </div>
    
    ${this.history.length > 1 ? this.generateHistoryChartHTML() : ''}
    
    <script id="ojhunt-history" type="application/json">
    ${JSON.stringify(this.history)}
    <\/script>
    
    <script>
        window.onload = function() {
            // Auto-trigger print dialog
        };
    <\/script>
</body>
</html>
            `;
        },
        
        /**
         * Initialize the component
         * @returns {void}
         */
        init() {
            if (this._initialized) return;
            this._initialized = true;
            
            this.loadSavedQueries();
            this.loadHistory();
            this.$nextTick(() => {
                document.addEventListener('keydown', (e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                        this.queryAll();
                    }
                });
                this.renderHistoryChart();
            });
        },
        
        /**
         * Render history chart using Canvas
         * @returns {void}
         */
        renderHistoryChart() {
            if (this.history.length < 2) return;
            
            const canvas = document.getElementById('history-chart');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;
            const padding = 40;
            
            ctx.clearRect(0, 0, width, height);
            
            const data = this.history.slice(-20);
            const maxSolved = Math.max(...data.map(d => d.totalSolved));
            
            const chartWidth = width - padding * 2;
            const chartHeight = height - padding * 2;
            const barWidth = chartWidth / data.length - 4;
            
            ctx.fillStyle = '#22863a';
            ctx.strokeStyle = '#ddd';
            
            ctx.beginPath();
            ctx.moveTo(padding, padding);
            ctx.lineTo(padding, height - padding);
            ctx.lineTo(width - padding, height - padding);
            ctx.stroke();
            
            data.forEach((entry, i) => {
                const barHeight = (entry.totalSolved / maxSolved) * chartHeight;
                const x = padding + i * (chartWidth / data.length) + 2;
                const y = height - padding - barHeight;
                
                ctx.fillStyle = '#4CAF50';
                ctx.fillRect(x, y, barWidth, barHeight);
                
                if (i % Math.ceil(data.length / 5) === 0) {
                    ctx.fillStyle = '#666';
                    ctx.font = '10px system-ui';
                    const date = new Date(entry.date).toLocaleDateString();
                    ctx.fillText(date, x, height - padding + 15);
                }
            });
            
            ctx.fillStyle = '#333';
            ctx.font = '12px system-ui';
            ctx.fillText('Solved Problems', padding, padding - 10);
        }
    };
}
