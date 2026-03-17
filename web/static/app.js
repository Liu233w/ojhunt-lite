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

const STORAGE_KEY = 'ojhunt-queries';

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
            this.$nextTick(() => {
                document.addEventListener('keydown', (e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                        this.queryAll();
                    }
                });
            });
        }
    };
}
