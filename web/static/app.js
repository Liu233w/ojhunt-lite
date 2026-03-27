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
 * @property {object | null} rawResponse - Verbatim API response, forwarded to /api/merge
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
        rawResponse: null,
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
            this.report = { totalSolved: null, totalSubmissions: 0 };
            
            try {
                const url = `/api/crawlers/${encodeURIComponent(q.crawler)}/${encodeURIComponent(q.username)}`;
                const response = await fetch(url, { signal: q.abortController.signal });
                const data = await response.json();
                
                q.rawResponse = data;
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
         * Calculate report by sending all executed query results to /api/merge.
         * The server handles VJudge deduplication.
         * @returns {Promise<void>}
         */
        async calculateReport() {
            if (this.queries.some(q => q.status === 'loading')) return;
            const executed = this.queries.filter(q => q.rawResponse !== null);
            if (executed.length === 0) {
                this.report = { totalSolved: 0, totalSubmissions: 0 };
                return;
            }
            const response = await fetch('/api/merge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(executed.map(q => q.rawResponse)),
            });
            const data = await response.json();
            this.report = {
                totalSolved: data.uniqueSolved,
                totalSubmissions: data.totalSubmissions,
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
