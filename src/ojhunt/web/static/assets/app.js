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

const STORAGE_KEY = 'ojhunt-queries';
const PDF_CACHE_KEY = 'ojhunt-report-pdf';
const PDF_CACHE_DATE_KEY = 'ojhunt-report-date';
const PDF_CACHE_FILENAME_KEY = 'ojhunt-report-filename';

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

/**
 * Remove the stored report — its bytes, date and filename are one record.
 * @returns {void}
 */
function clearStoredReport() {
    localStorage.removeItem(PDF_CACHE_KEY);
    localStorage.removeItem(PDF_CACHE_DATE_KEY);
    localStorage.removeItem(PDF_CACHE_FILENAME_KEY);
}

/**
 * Store the cached report.
 * Drops the stored record before writing the new one. Browser storage may refuse
 * the write, and a surviving older record would read as the latest report. Losing
 * the record is acceptable, presenting the wrong one is not — so a rejected write
 * needs no handling beyond the removal that already happened.
 * @param {{b64: string, date: string, filename: string}} record
 * @returns {void}
 */
function cacheReport(record) {
    clearStoredReport();
    try {
        localStorage.setItem(PDF_CACHE_KEY, record.b64);
        localStorage.setItem(PDF_CACHE_DATE_KEY, record.date);
        localStorage.setItem(PDF_CACHE_FILENAME_KEY, record.filename);
    } catch (_) {}
}

/**
 * Read the stored report. The three keys are written in one pass, so a fragment
 * means the write was cut short, or another tab or an eviction took a key. Half a
 * record cannot be trusted to describe one report, so it is dropped.
 * @returns {{b64: string, date: string, filename: string} | null}
 */
function readCachedReport() {
    const record = {
        b64: localStorage.getItem(PDF_CACHE_KEY),
        date: localStorage.getItem(PDF_CACHE_DATE_KEY),
        filename: localStorage.getItem(PDF_CACHE_FILENAME_KEY),
    };
    if (Object.values(record).every(Boolean)) return record;

    clearStoredReport();
    return null;
}

/**
 * Make the browser save a PDF. Uses a data URL — no Blob/createObjectURL needed.
 * @param {string} b64
 * @param {string} filename
 * @returns {void}
 */
function triggerPdfDownload(b64, filename) {
    const a = document.createElement('a');
    a.href = 'data:application/pdf;base64,' + b64;
    a.download = filename;
    a.click();
}

function ojhunt() {
    return {
        isMac: /Mac|iPhone|iPad|iPod/.test(navigator.platform),

        /** @type {Object<string, {title: string, description: string, isAggregator: boolean}>} */
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

        /** @type {AbortController | null} In-flight /api/merge request, for cancellation */
        _mergeController: null,

        /**
         * The loaded report, or null. Holds its own bytes, so the session serves it
         * from memory and never depends on what browser storage accepted.
         * @type {{b64: string, date: string, filename: string} | null}
         */
        cachedReport: null,

        /** @type {boolean} True while the user is dragging a file over the report slot */
        isDragging: false,

        /** @type {boolean} True while a PDF is being generated */
        isDownloading: false,

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
                if (response.status === 429) {
                    q.status = 'error';
                    q.error = 'Rate limit exceeded. Please wait a moment and try again.';
                    return;
                }
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
        },

        /**
         * Retry a query
         * @param {string} id
         * @returns {Promise<void>}
         */
        async retryQuery(id) {
            await this.executeQuery(id);
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

            await Promise.all(pendingQueries.map(q => this.executeQuery(q.id)));
        },

        /**
         * Clear all queries
         * @returns {void}
         */
        clearAll() {
            this.queries = [];
        },

        /**
         * Calculate report by sending all executed query results to /api/merge.
         * The server handles VJudge deduplication.
         * Cancels any in-flight merge request to avoid stale results from concurrent completions.
         * @returns {Promise<void>}
         */
        async calculateReport() {
            if (this.queries.some(q => q.status === 'loading')) return;
            const executed = this.queries.filter(q => q.rawResponse !== null);
            if (executed.length === 0) {
                this.report = { totalSolved: this.queries.length === 0 ? null : 0, totalSubmissions: 0 };
                return;
            }

            if (this._mergeController) this._mergeController.abort();
            this._mergeController = new AbortController();

            try {
                const response = await fetch('/api/merge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(executed.map(q => q.rawResponse)),
                    signal: this._mergeController.signal,
                });
                if (response.status === 429) {
                    alert('Rate limit exceeded. Please wait a moment and try again.');
                    return;
                }
                const data = await response.json();
                this.report = {
                    totalSolved: data.uniqueSolved,
                    totalSubmissions: data.totalSubmissions,
                };
            } catch (e) {
                if (e.name !== 'AbortError') throw e;
            } finally {
                this._mergeController = null;
            }
        },

        /**
         * Save queries to localStorage
         * @returns {void}
         */
        saveQueries() {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify({
                    username: this.username,
                    queries: this.queries.map(q => ({ crawler: q.crawler, username: q.username }))
                }));
            } catch (_) {}
        },

        /**
         * Load saved queries and the cached report from localStorage.
         * @returns {void}
         */
        loadSavedQueries() {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
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
            }

            this.cachedReport = readCachedReport();
        },

        /**
         * Forget the loaded report. The $watch clears its keys.
         * @returns {void}
         */
        clearCachedReport() {
            this.cachedReport = null;
        },

        /**
         * Save the loaded report to the user's device.
         * @returns {void}
         */
        downloadCachedReport() {
            if (!this.cachedReport) return;
            triggerPdfDownload(this.cachedReport.b64, this.cachedReport.filename);
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
         * Upload a previous OJHunt PDF report.
         * Always saves the PDF to the cache. If the query table is empty, populates it
         * from the PDF settings. If non-empty, asks the user whether to overwrite.
         * @param {File} file
         * @returns {Promise<void>}
         */
        async uploadReport(file) {
            // Read file as base64
            let b64;
            try {
                b64 = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
            } catch (e) {
                alert('Failed to read file: ' + e.message);
                return;
            }

            let data;
            try {
                const response = await fetch('/api/pdf/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pdf_b64: b64 }),
                });
                if (!response.ok) {
                    const err = await response.json();
                    alert(err.detail || 'Failed to read PDF');
                    return;
                }
                data = await response.json();
            } catch (e) {
                alert('Failed to read PDF: ' + e.message);
                return;
            }

            // The record needs a date, which comes from the newest history entry. A PDF
            // without history carries settings only, and has no history to load.
            if (data.report_date) {
                this.cachedReport = { b64, date: data.report_date, filename: file.name };
            }

            // Apply settings to the live UI
            if (this.queries.length === 0) {
                this.username = data.settings.username;
                for (const q of data.settings.queries) {
                    if (q.crawler && q.username && this.crawlers[q.crawler] && !this.queryExists(q.crawler, q.username)) {
                        this.queries.push(createQuery(q.crawler, q.username, this.queryIdCounter++));
                    }
                }
            } else if (confirm('Overwrite your current crawler list with the one from this PDF?')) {
                this.username = data.settings.username;
                this.queries = data.settings.queries
                    .filter(q => q.crawler && q.username && this.crawlers[q.crawler])
                    .map(q => createQuery(q.crawler, q.username, this.queryIdCounter++));
            }
        },

        /**
         * Download a progress report PDF, merging current results with cached history.
         * Updates the localStorage cache with the newly generated PDF.
         * @returns {Promise<void>}
         */
        async downloadReport() {
            this.isDownloading = true;
            try {
                const request = {
                    snapshot: {
                        totalSolved: this.report.totalSolved,
                        totalSubmissions: this.report.totalSubmissions,
                        username: this.username,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        results: this.queries
                            .filter(q => q.status === 'success')
                            .map(q => ({ crawler: q.crawler, username: q.username, solved: q.solved, submissions: q.submissions })),
                    },
                    settings: {
                        username: this.username,
                        queries: this.queries.map(q => ({ crawler: q.crawler, username: q.username })),
                    },
                    previous_pdf_b64: this.cachedReport?.b64 || null,
                };

                let data;
                try {
                    const response = await fetch('/api/pdf/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(request),
                    });
                    if (response.status === 429) {
                        alert('Rate limit exceeded. Please wait a moment and try again.');
                        return;
                    }
                    if (!response.ok) {
                        const err = await response.json();
                        alert(err.detail || 'Failed to generate PDF');
                        return;
                    }
                    data = await response.json();
                } catch (e) {
                    alert('Failed to generate PDF: ' + e.message);
                    return;
                }

                this.cachedReport = {
                    b64: data.pdf_b64,
                    date: data.date,
                    filename: `ojhunt-report-${data.date}.pdf`,
                };

                triggerPdfDownload(this.cachedReport.b64, this.cachedReport.filename);
            } finally {
                this.isDownloading = false;
            }
        },

        /**
         * Initialize the component
         * @returns {void}
         */
        init() {
            if (this._initialized) return;
            this._initialized = true;

            this.loadSavedQueries();

            // Auto-sync config to localStorage (replaces scattered saveQueries() call sites)
            this.$watch('username', () => this.saveQueries());
            this.$watch('queries', () => {
                this.saveQueries();
                this.calculateReport();
            });

            // Sync the loaded report to localStorage
            this.$watch('cachedReport', record => {
                if (record) cacheReport(record);
                else clearStoredReport();
            });

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
