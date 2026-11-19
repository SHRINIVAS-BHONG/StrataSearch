/**
 * StrataSearch Enterprise Hybrid Retrieval & Document Intelligence
 * Zero-Framework Vanilla JavaScript Controller
 * 
 * Strict Vanilla ES6+ Architecture:
 * - NavigationController: Workspace tab switching & global keyboard shortcuts
 * - SearchController: Hybrid RRF retrieval, telemetry strip & full context modal
 * - KnowledgeBaseController: Drag-and-drop uploader, URL importer, smart polling table
 * - TelemetryController: Real-time health probes, KPI cards, cache purge & cURL tabs
 * - ToastManager: Non-blocking enterprise notifications
 */

(function () {
  'use strict';

  // =========================================================================
  // Utilities & Helpers
  // =========================================================================

  function escapeHtml(text) {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }

  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const val = (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1);
    return `${val} ${units[i]}`;
  }

  function formatDate(isoStr) {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoStr;
    }
  }

  // =========================================================================
  // Toast Manager
  // =========================================================================

  const ToastManager = {
    container: null,

    init() {
      this.container = document.getElementById('toast-container');
    },

    show(message, type = 'info', durationMs = 4000) {
      if (!this.container) return;

      const toast = document.createElement('div');
      toast.className = `strata-toast ${type}`;

      const iconMap = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
      };

      toast.innerHTML = `
        <span style="font-weight:700;">${iconMap[type] || 'ℹ'}</span>
        <span style="flex:1;">${escapeHtml(message)}</span>
      `;

      this.container.appendChild(toast);

      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
      }, durationMs);
    }
  };

  // =========================================================================
  // Navigation Controller
  // =========================================================================

  const NavigationController = {
    tabButtons: [],
    panels: [],

    init() {
      this.tabButtons = Array.from(document.querySelectorAll('.tab-btn'));
      this.panels = Array.from(document.querySelectorAll('.workspace-panel'));

      this.tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          const targetTabId = btn.getAttribute('data-tab');
          this.switchTab(targetTabId);
        });
      });

      // Global keyboard shortcuts
      window.addEventListener('keydown', (e) => {
        // Alt+1, Alt+2, Alt+3 for workspaces
        if (e.altKey && e.key === '1') {
          e.preventDefault();
          this.switchTab('tab-search');
        } else if (e.altKey && e.key === '2') {
          e.preventDefault();
          this.switchTab('tab-knowledge');
        } else if (e.altKey && e.key === '3') {
          e.preventDefault();
          this.switchTab('tab-telemetry');
        }

        // "/" key focuses search bar (unless currently in an input/textarea)
        if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
          e.preventDefault();
          this.switchTab('tab-search');
          const searchInput = document.getElementById('search-query-input');
          if (searchInput) searchInput.focus();
        }

        // Escape closes any open modals
        if (e.key === 'Escape') {
          SearchController.closeModal();
          KnowledgeBaseController.closeDeleteModal();
        }
      });
    },

    switchTab(targetTabId) {
      this.tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === targetTabId) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      this.panels.forEach(panel => {
        if (panel.id === targetTabId) {
          panel.classList.add('active');
        } else {
          panel.classList.remove('active');
        }
      });
    }
  };

  // =========================================================================
  // Search Controller
  // =========================================================================

  const SearchController = {
    form: null,
    input: null,
    clearBtn: null,
    modeSelect: null,
    topKSlider: null,
    topKVal: null,
    rrfKInput: null,
    scopeSelect: null,
    resultsContainer: null,
    telemetryStrip: null,
    spinner: null,

    // Modal elements
    modalOverlay: null,
    modalTitle: null,
    modalMeta: null,
    modalText: null,
    modalJson: null,
    currentResults: [],

    init() {
      this.form = document.getElementById('search-form');
      this.input = document.getElementById('search-query-input');
      this.clearBtn = document.getElementById('clear-search-btn');
      this.modeSelect = document.getElementById('search-mode-select');
      this.topKSlider = document.getElementById('top-k-slider');
      this.topKVal = document.getElementById('top-k-val');
      this.rrfKInput = document.getElementById('rrf-k-input');
      this.scopeSelect = document.getElementById('scope-filter-select');
      this.resultsContainer = document.getElementById('search-results-container');
      this.telemetryStrip = document.getElementById('telemetry-strip');
      this.spinner = document.getElementById('search-spinner');

      this.modalOverlay = document.getElementById('modal-chunk-context');
      this.modalTitle = document.getElementById('modal-chunk-title');
      this.modalMeta = document.getElementById('modal-chunk-meta');
      this.modalText = document.getElementById('modal-chunk-text');
      this.modalJson = document.getElementById('modal-chunk-json');

      if (this.topKSlider && this.topKVal) {
        this.topKSlider.addEventListener('input', () => {
          this.topKVal.textContent = this.topKSlider.value;
        });
      }

      if (this.input && this.clearBtn) {
        this.input.addEventListener('input', () => {
          this.clearBtn.style.display = this.input.value.trim() ? 'inline-block' : 'none';
        });

        this.clearBtn.addEventListener('click', () => {
          this.input.value = '';
          this.clearBtn.style.display = 'none';
          this.input.focus();
        });
      }

      if (this.form) {
        this.form.addEventListener('submit', (e) => {
          e.preventDefault();
          this.executeSearch();
        });
      }

      const closeContextBtn = document.getElementById('btn-close-context-modal');
      const dismissContextBtn = document.getElementById('btn-dismiss-context');
      if (closeContextBtn) closeContextBtn.addEventListener('click', () => this.closeModal());
      if (dismissContextBtn) dismissContextBtn.addEventListener('click', () => this.closeModal());

      if (this.modalOverlay) {
        this.modalOverlay.addEventListener('click', (e) => {
          if (e.target === this.modalOverlay) this.closeModal();
        });
      }
    },

    async executeSearch() {
      const query = (this.input.value || '').trim();
      if (!query) {
        ToastManager.show('Please enter a search query', 'warning');
        return;
      }

      const topK = parseInt(this.topKSlider.value, 10) || 5;
      const mode = this.modeSelect.value || 'hybrid';
      const rrfK = parseInt(this.rrfKInput.value, 10) || 60;
      const scopeFilter = this.scopeSelect.value || null;

      const payload = {
        query: query,
        top_k: topK,
        mode: mode,
        rrf_k: rrfK,
        source_filter: scopeFilter
      };

      if (this.spinner) this.spinner.style.display = 'inline-block';

      try {
        const res = await fetch('/api/v1/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Search failed with status ${res.status}`);
        }

        const data = await res.json();
        this.currentResults = data.results || [];
        this.renderTelemetry(data);
        this.renderResults(data, query);
      } catch (err) {
        ToastManager.show(err.message, 'error');
        this.resultsContainer.innerHTML = `
          <div class="strata-card empty-state">
            <div class="empty-state-icon" style="color:var(--accent-rose);">✕</div>
            <div class="empty-state-title">Retrieval Error</div>
            <p class="empty-state-desc">${escapeHtml(err.message)}</p>
          </div>
        `;
      } finally {
        if (this.spinner) this.spinner.style.display = 'none';
      }
    },

    renderTelemetry(data) {
      if (!this.telemetryStrip) return;
      this.telemetryStrip.classList.add('active');

      const latencyEl = document.getElementById('tel-latency');
      const cacheEl = document.getElementById('tel-cache');
      const strategyEl = document.getElementById('tel-strategy');
      const hitsEl = document.getElementById('tel-hits');

      if (latencyEl) {
        latencyEl.textContent = `${(data.latency_ms || 0).toFixed(1)} ms`;
      }

      if (cacheEl) {
        if (data.cache_hit) {
          cacheEl.className = 'telemetry-val cache-hit';
          cacheEl.textContent = 'HIT (Redis SHA-256)';
        } else {
          cacheEl.className = 'telemetry-val cache-miss';
          cacheEl.textContent = 'MISS (Live Database)';
        }
      }

      if (strategyEl) {
        strategyEl.textContent = (data.strategy_used || 'HYBRID RRF').toUpperCase();
      }

      if (hitsEl) {
        hitsEl.textContent = data.total_hits !== undefined ? data.total_hits : (data.results ? data.results.length : 0);
      }
    },

    highlightKeywords(text, query, matchedTerms) {
      if (!text) return '';
      let terms = [];
      if (Array.isArray(matchedTerms) && matchedTerms.length > 0) {
        terms = matchedTerms;
      } else if (query) {
        terms = query.split(/\s+/).filter(w => w.length > 2);
      }

      if (terms.length === 0) return escapeHtml(text);

      const escapedTerms = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
      const pattern = new RegExp(`(${escapedTerms.join('|')})`, 'gi');

      // Escape text first, then highlight
      const safe = escapeHtml(text);
      return safe.replace(pattern, '<mark>$1</mark>');
    },

    renderResults(data, query) {
      const results = data.results || [];
      if (results.length === 0) {
        this.resultsContainer.innerHTML = `
          <div class="strata-card empty-state">
            <div class="empty-state-icon">🔍</div>
            <div class="empty-state-title">No Matching Documents Found</div>
            <p class="empty-state-desc">Try adjusting your query, widening the Top-K parameter, or clearing the document scope filter.</p>
          </div>
        `;
        return;
      }

      let html = '';
      results.forEach((item, index) => {
        const rank = index + 1;
        const filename = item.filename || item.source_id || `document_${item.chunk_id}`;
        const sourceExt = filename.includes('.') ? filename.split('.').pop() : 'DOC';
        const chunkIdx = item.chunk_index !== undefined ? item.chunk_index : index;

        const denseBadge = item.dense_rank !== null && item.dense_rank !== undefined
          ? `<span class="score-chip dense" title="Dense Vector HNSW Rank">Dense #${item.dense_rank}</span>`
          : '';

        const sparseBadge = item.sparse_rank !== null && item.sparse_rank !== undefined
          ? `<span class="score-chip sparse" title="Sparse Inverted GIN Rank">Sparse #${item.sparse_rank}</span>`
          : '';

        const scoreVal = typeof item.score === 'number' ? item.score.toFixed(6) : item.score;
        const rrfBadge = `<span class="score-chip rrf" title="Calibrated RRF Composite Score">RRF: ${scoreVal}</span>`;

        const snippet = this.highlightKeywords(item.content, query, item.matched_terms);

        html += `
          <div class="search-result-card" data-result-index="${index}">
            <div class="result-card-header">
              <div class="result-meta-left">
                <span class="rank-badge">#${rank}</span>
                <span class="source-badge">${escapeHtml(sourceExt)}</span>
                <span class="doc-name-chip">${escapeHtml(filename)}</span>
                <span class="chunk-index-chip">[chunk #${chunkIdx}]</span>
              </div>
              <div class="result-scores-right">
                ${denseBadge}
                ${sparseBadge}
                ${rrfBadge}
              </div>
            </div>
            <div class="result-content-snippet">${snippet}</div>
            <div class="result-card-footer">
              <button type="button" class="btn-inspect-context" onclick="window.StrataApp.inspectContext(${index})">
                <span>Inspect Full Context</span> ↗
              </button>
            </div>
          </div>
        `;
      });

      this.resultsContainer.innerHTML = html;
    },

    openContextModal(index) {
      const item = this.currentResults[index];
      if (!item) return;

      const filename = item.filename || item.source_id || `Chunk #${item.chunk_id}`;
      const chunkIdx = item.chunk_index !== undefined ? item.chunk_index : index;

      this.modalTitle.textContent = `${filename} (Chunk #${chunkIdx})`;
      this.modalMeta.textContent = `Chunk ID: ${item.chunk_id || '—'} · Source ID: ${item.source_id || '—'} · Score: ${item.score}`;
      this.modalText.textContent = item.content || '';
      this.modalJson.textContent = JSON.stringify(item, null, 2);

      this.modalOverlay.classList.add('active');
      this.modalOverlay.setAttribute('aria-hidden', 'false');
    },

    closeModal() {
      if (!this.modalOverlay) return;
      this.modalOverlay.classList.remove('active');
      this.modalOverlay.setAttribute('aria-hidden', 'true');
    }
  };

  // =========================================================================
  // Knowledge Base Controller
  // =========================================================================

  const KnowledgeBaseController = {
    dropZone: null,
    fileInput: null,
    stagedFilesList: null,
    btnClearStaged: null,
    btnUploadFiles: null,
    progressWrapper: null,
    progressBar: null,
    urlForm: null,
    urlInput: null,
    urlSpinner: null,
    tableSearchInput: null,
    tableBody: null,
    refreshBtn: null,
    statusFilterButtons: [],

    // Staging and Data state
    stagedFiles: [],
    documentsList: [],
    currentStatusFilter: 'ALL',
    deleteTargetId: null,
    deleteModal: null,
    deleteDocNameEl: null,
    pollingTimer: null,

    init() {
      this.dropZone = document.getElementById('drop-zone');
      this.fileInput = document.getElementById('file-input');
      this.stagedFilesList = document.getElementById('staged-files-list');
      this.btnClearStaged = document.getElementById('btn-clear-staged');
      this.btnUploadFiles = document.getElementById('btn-upload-files');
      this.progressWrapper = document.getElementById('upload-progress-wrapper');
      this.progressBar = document.getElementById('upload-progress-bar');
      this.urlForm = document.getElementById('url-import-form');
      this.urlInput = document.getElementById('url-input');
      this.urlSpinner = document.getElementById('url-spinner');
      this.tableSearchInput = document.getElementById('table-search-input');
      this.tableBody = document.getElementById('doc-library-tbody');
      this.refreshBtn = document.getElementById('btn-refresh-docs');
      this.statusFilterButtons = Array.from(document.querySelectorAll('.status-chip-btn'));

      this.deleteModal = document.getElementById('modal-delete-confirm');
      this.deleteDocNameEl = document.getElementById('delete-doc-name');

      // Dropzone event listeners
      if (this.dropZone && this.fileInput) {
        this.dropZone.addEventListener('click', () => this.fileInput.click());

        this.dropZone.addEventListener('dragover', (e) => {
          e.preventDefault();
          this.dropZone.classList.add('dragover');
        });

        this.dropZone.addEventListener('dragleave', () => {
          this.dropZone.classList.remove('dragover');
        });

        this.dropZone.addEventListener('drop', (e) => {
          e.preventDefault();
          this.dropZone.classList.remove('dragover');
          if (e.dataTransfer && e.dataTransfer.files) {
            this.handleFiles(Array.from(e.dataTransfer.files));
          }
        });

        this.fileInput.addEventListener('change', () => {
          if (this.fileInput.files) {
            this.handleFiles(Array.from(this.fileInput.files));
          }
        });
      }

      if (this.btnClearStaged) {
        this.btnClearStaged.addEventListener('click', () => {
          this.stagedFiles = [];
          this.renderStagedFiles();
        });
      }

      if (this.btnUploadFiles) {
        this.btnUploadFiles.addEventListener('click', () => this.uploadStagedFiles());
      }

      if (this.urlForm) {
        this.urlForm.addEventListener('submit', (e) => {
          e.preventDefault();
          this.submitUrl();
        });
      }

      if (this.refreshBtn) {
        this.refreshBtn.addEventListener('click', () => this.fetchDocuments(true));
      }

      if (this.tableSearchInput) {
        this.tableSearchInput.addEventListener('input', () => this.renderTable());
      }

      this.statusFilterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          this.statusFilterButtons.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          this.currentStatusFilter = btn.getAttribute('data-status-filter') || 'ALL';
          this.renderTable();
        });
      });

      // Delete confirmation modal bindings
      const btnCancelDelete = document.getElementById('btn-cancel-delete');
      const btnConfirmDelete = document.getElementById('btn-confirm-delete');
      const btnCloseDeleteModal = document.getElementById('btn-close-delete-modal');

      if (btnCancelDelete) btnCancelDelete.addEventListener('click', () => this.closeDeleteModal());
      if (btnCloseDeleteModal) btnCloseDeleteModal.addEventListener('click', () => this.closeDeleteModal());
      if (btnConfirmDelete) btnConfirmDelete.addEventListener('click', () => this.executeDelete());

      if (this.deleteModal) {
        this.deleteModal.addEventListener('click', (e) => {
          if (e.target === this.deleteModal) this.closeDeleteModal();
        });
      }

      // Initial fetch and start smart polling
      this.fetchDocuments();
      this.startSmartPolling();
    },

    handleFiles(files) {
      const MAX_SIZE = 25 * 1024 * 1024; // 25 MB limit
      const allowedExts = ['.pdf', '.docx', '.txt', '.md', '.csv'];

      files.forEach(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedExts.includes(ext)) {
          ToastManager.show(`Skipped "${file.name}": unsupported extension (${ext})`, 'warning');
          return;
        }

        if (file.size > MAX_SIZE) {
          ToastManager.show(`Skipped "${file.name}": exceeds 25MB limit (${formatBytes(file.size)})`, 'error');
          return;
        }

        // Avoid exact duplicates in staging
        if (!this.stagedFiles.some(f => f.name === file.name && f.size === file.size)) {
          this.stagedFiles.push(file);
        }
      });

      this.renderStagedFiles();
    },

    renderStagedFiles() {
      if (!this.stagedFilesList) return;

      if (this.stagedFiles.length === 0) {
        this.stagedFilesList.innerHTML = '';
        if (this.btnClearStaged) this.btnClearStaged.style.display = 'none';
        if (this.btnUploadFiles) this.btnUploadFiles.style.display = 'none';
        return;
      }

      if (this.btnClearStaged) this.btnClearStaged.style.display = 'inline-flex';
      if (this.btnUploadFiles) this.btnUploadFiles.style.display = 'inline-flex';

      let html = '';
      this.stagedFiles.forEach((file, idx) => {
        html += `
          <div class="staged-file-item">
            <div class="staged-file-info">
              <span>📄</span>
              <span style="font-weight:500;">${escapeHtml(file.name)}</span>
              <span class="num-tabular" style="color:var(--text-muted); font-size:0.75rem;">(${formatBytes(file.size)})</span>
            </div>
            <button type="button" class="btn-remove-staged" onclick="window.StrataApp.removeStagedFile(${idx})" title="Remove">✕</button>
          </div>
        `;
      });

      this.stagedFilesList.innerHTML = html;
    },

    removeStagedFile(index) {
      this.stagedFiles.splice(index, 1);
      this.renderStagedFiles();
    },

    async uploadStagedFiles() {
      if (this.stagedFiles.length === 0) return;

      const formData = new FormData();
      this.stagedFiles.forEach(file => {
        formData.append('files', file);
      });

      if (this.progressWrapper) this.progressWrapper.classList.add('active');
      if (this.progressBar) this.progressBar.style.width = '45%';
      if (this.btnUploadFiles) this.btnUploadFiles.disabled = true;

      try {
        const res = await fetch('/api/v1/documents/upload', {
          method: 'POST',
          body: formData
        });

        if (this.progressBar) this.progressBar.style.width = '90%';

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Upload failed with status ${res.status}`);
        }

        const data = await res.json();
        const uploadedCount = Array.isArray(data) ? data.length : (data.documents ? data.documents.length : this.stagedFiles.length);

        ToastManager.show(`Successfully enqueued ${uploadedCount} document(s) for indexing`, 'success');
        this.stagedFiles = [];
        this.renderStagedFiles();
        await this.fetchDocuments(true);
      } catch (err) {
        ToastManager.show(err.message, 'error');
      } finally {
        if (this.progressBar) this.progressBar.style.width = '100%';
        setTimeout(() => {
          if (this.progressWrapper) this.progressWrapper.classList.remove('active');
          if (this.progressBar) this.progressBar.style.width = '0%';
        }, 400);
        if (this.btnUploadFiles) this.btnUploadFiles.disabled = false;
      }
    },

    async submitUrl() {
      const url = (this.urlInput.value || '').trim();
      if (!url) {
        ToastManager.show('Please enter a valid URL', 'warning');
        return;
      }

      if (this.urlSpinner) this.urlSpinner.style.display = 'inline-block';

      try {
        const res = await fetch('/api/v1/documents/url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `URL ingestion failed (${res.status})`);
        }

        ToastManager.show('URL registered and enqueued for indexing', 'success');
        this.urlInput.value = '';
        await this.fetchDocuments(true);
      } catch (err) {
        ToastManager.show(err.message, 'error');
      } finally {
        if (this.urlSpinner) this.urlSpinner.style.display = 'none';
      }
    },

    async fetchDocuments(manual = false) {
      try {
        const res = await fetch('/api/v1/documents');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        this.documentsList = data.documents || [];

        // Update corpus counter in header & telemetry KPI
        this.updateCorpusCounters(data);

        // Update search scope filter options
        this.updateSearchScopeDropdown();

        // Update Split-flap status count chips
        this.updateStatusFilterCounts();

        // Render table
        this.renderTable();

        if (manual) {
          ToastManager.show('Document registry refreshed', 'info', 2000);
        }
      } catch (err) {
        console.warn('Failed to fetch documents:', err);
        if (manual) {
          ToastManager.show('Failed to refresh document registry', 'error');
        }
      }
    },

    updateCorpusCounters(data) {
      const totalDocs = data.total_documents !== undefined ? data.total_documents : this.documentsList.length;
      let totalChunks = data.total_chunks !== undefined ? data.total_chunks : 0;
      let totalBytes = data.total_size_bytes !== undefined ? data.total_size_bytes : 0;

      if (data.total_chunks === undefined) {
        totalChunks = this.documentsList.reduce((acc, doc) => acc + (doc.chunk_count || 0), 0);
      }
      if (data.total_size_bytes === undefined) {
        totalBytes = this.documentsList.reduce((acc, doc) => acc + (doc.file_size_bytes || 0), 0);
      }

      const docsCountEl = document.getElementById('corpus-docs-count');
      const chunksCountEl = document.getElementById('corpus-chunks-count');
      if (docsCountEl) docsCountEl.textContent = `${totalDocs} Docs`;
      if (chunksCountEl) chunksCountEl.textContent = `${totalChunks} Chunks`;

      // Update KPI cards in Telemetry workspace
      const kpiDocs = document.getElementById('kpi-total-docs');
      const kpiChunks = document.getElementById('kpi-total-chunks');
      const kpiStorage = document.getElementById('kpi-storage-vol');

      if (kpiDocs) kpiDocs.textContent = totalDocs.toLocaleString();
      if (kpiChunks) kpiChunks.textContent = totalChunks.toLocaleString();
      if (kpiStorage) kpiStorage.textContent = formatBytes(totalBytes);
    },

    updateSearchScopeDropdown() {
      const select = document.getElementById('scope-filter-select');
      if (!select) return;

      const currentVal = select.value;
      let optionsHtml = '<option value="">All Indexed Documents</option>';

      this.documentsList.forEach(doc => {
        const id = doc.doc_id || doc.filename;
        const name = doc.filename || id;
        optionsHtml += `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`;
      });

      select.innerHTML = optionsHtml;
      select.value = currentVal;
    },

    updateStatusFilterCounts() {
      const counts = {
        ALL: this.documentsList.length,
        INDEXED: 0,
        PROCESSING: 0,
        QUEUED: 0,
        FAILED: 0
      };

      this.documentsList.forEach(doc => {
        const st = (doc.status || '').toUpperCase();
        if (counts[st] !== undefined) {
          counts[st]++;
        }
      });

      const elAll = document.getElementById('count-filter-all');
      const elIndexed = document.getElementById('count-filter-indexed');
      const elProc = document.getElementById('count-filter-processing');
      const elQueued = document.getElementById('count-filter-queued');
      const elFailed = document.getElementById('count-filter-failed');

      if (elAll) elAll.textContent = counts.ALL;
      if (elIndexed) elIndexed.textContent = counts.INDEXED;
      if (elProc) elProc.textContent = counts.PROCESSING;
      if (elQueued) elQueued.textContent = counts.QUEUED;
      if (elFailed) elFailed.textContent = counts.FAILED;
    },

    renderTable() {
      if (!this.tableBody) return;

      const searchTerm = (this.tableSearchInput ? this.tableSearchInput.value : '').toLowerCase().trim();
      const statusFilter = this.currentStatusFilter;

      let filtered = this.documentsList.filter(doc => {
        const filename = (doc.filename || '').toLowerCase();
        if (searchTerm && !filename.includes(searchTerm)) return false;

        if (statusFilter !== 'ALL') {
          if ((doc.status || '').toUpperCase() !== statusFilter) return false;
        }
        return true;
      });

      if (filtered.length === 0) {
        this.tableBody.innerHTML = `
          <tr>
            <td colspan="6" class="empty-state">
              ${this.documentsList.length === 0 ? 'No documents indexed yet. Upload documents or ingest URLs above.' : 'No documents matching active filters.'}
            </td>
          </tr>
        `;
        return;
      }

      let html = '';
      filtered.forEach(doc => {
        const status = (doc.status || 'queued').toLowerCase();
        const docId = doc.doc_id || doc.id || '';
        const filename = doc.filename || 'Untitled';
        const sourceType = (doc.source_type || 'doc').toUpperCase();
        const sizeFormatted = formatBytes(doc.file_size_bytes);
        const chunkCount = doc.chunk_count !== undefined ? doc.chunk_count : 0;
        const dateFormatted = formatDate(doc.created_at);

        html += `
          <tr>
            <td>
              <span class="status-badge ${status}">
                <span class="status-dot"></span>
                <span>${status}</span>
              </span>
            </td>
            <td>
              <div style="display:flex; align-items:center; gap:0.5rem;">
                <span class="source-badge">${escapeHtml(sourceType)}</span>
                <span style="font-weight:500; color:var(--text-primary);">${escapeHtml(filename)}</span>
              </div>
            </td>
            <td class="num-tabular">${sizeFormatted}</td>
            <td class="num-tabular">${chunkCount} chunks</td>
            <td class="num-tabular" style="color:var(--text-muted); font-size:0.75rem;">${dateFormatted}</td>
            <td style="text-align: right;">
              <div class="table-actions" style="justify-content: flex-end;">
                <button type="button" class="btn-table-action" onclick="window.StrataApp.filterInSearch('${escapeHtml(docId)}')" title="Search only this document">
                  <span>Scope</span>
                </button>
                <button type="button" class="btn-danger" onclick="window.StrataApp.promptDelete('${escapeHtml(docId)}', '${escapeHtml(filename)}')" title="Delete document">
                  <span>✕</span>
                </button>
              </div>
            </td>
          </tr>
        `;
      });

      this.tableBody.innerHTML = html;
    },

    promptDelete(docId, docName) {
      this.deleteTargetId = docId;
      if (this.deleteDocNameEl) {
        this.deleteDocNameEl.textContent = `"${docName}"`;
      }
      if (this.deleteModal) {
        this.deleteModal.classList.add('active');
        this.deleteModal.setAttribute('aria-hidden', 'false');
      }
    },

    closeDeleteModal() {
      this.deleteTargetId = null;
      if (this.deleteModal) {
        this.deleteModal.classList.remove('active');
        this.deleteModal.setAttribute('aria-hidden', 'true');
      }
    },

    async executeDelete() {
      if (!this.deleteTargetId) return;
      const targetId = this.deleteTargetId;

      try {
        const res = await fetch(`/api/v1/documents/${encodeURIComponent(targetId)}`, {
          method: 'DELETE'
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Deletion failed (${res.status})`);
        }

        ToastManager.show('Document and associated vector chunks purged', 'success');
        this.closeDeleteModal();
        await this.fetchDocuments(true);
      } catch (err) {
        ToastManager.show(err.message, 'error');
      }
    },

    startSmartPolling() {
      if (this.pollingTimer) clearInterval(this.pollingTimer);

      const checkInterval = () => {
        // Fast poll (4s) if any document is in queued or processing state
        const hasPending = this.documentsList.some(d => {
          const s = (d.status || '').toLowerCase();
          return s === 'queued' || s === 'processing';
        });

        const nextInterval = hasPending ? 4000 : 15000;
        this.fetchDocuments();
        this.pollingTimer = setTimeout(checkInterval, nextInterval);
      };

      this.pollingTimer = setTimeout(checkInterval, 4000);
    }
  };

  // =========================================================================
  // Telemetry Controller
  // =========================================================================

  const TelemetryController = {
    btnProbeHealth: null,
    btnPurgeCache: null,
    btnCopyCurl: null,
    curlTabs: [],
    curlSnippetCode: null,
    currentCurlType: 'search',

    curlTemplates: {
      search: `# Hybrid RRF Search
curl -X POST "http://localhost:8000/api/v1/search" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "quarterly revenue metrics", "top_k": 5, "mode": "hybrid", "rrf_k": 60}'`,

      upload: `# Multipart Multi-File Ingestion
curl -X POST "http://localhost:8000/api/v1/documents/upload" \\
  -F "files=@financial_report.pdf" \\
  -F "files=@handbook.docx"`,

      url: `# Web Article & Documentation Readability Ingestion
curl -X POST "http://localhost:8000/api/v1/documents/url" \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://docs.enterprise.com/architecture-spec.html"}'`,

      health: `# Live Subsystem Diagnostics Probe
curl -X GET "http://localhost:8000/api/v1/health"`
    },

    init() {
      this.btnProbeHealth = document.getElementById('btn-probe-health');
      this.btnPurgeCache = document.getElementById('btn-purge-cache');
      this.btnCopyCurl = document.getElementById('btn-copy-curl');
      this.curlSnippetCode = document.getElementById('curl-snippet-code');
      this.curlTabs = Array.from(document.querySelectorAll('.curl-tab-btn'));

      if (this.btnProbeHealth) {
        this.btnProbeHealth.addEventListener('click', () => this.probeHealth(true));
      }

      if (this.btnPurgeCache) {
        this.btnPurgeCache.addEventListener('click', () => this.purgeCache());
      }

      if (this.btnCopyCurl) {
        this.btnCopyCurl.addEventListener('click', () => this.copyCurl());
      }

      this.curlTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          this.curlTabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          this.currentCurlType = tab.getAttribute('data-curl') || 'search';
          if (this.curlSnippetCode) {
            this.curlSnippetCode.textContent = this.curlTemplates[this.currentCurlType] || '';
          }
        });
      });

      // Initial probe
      this.probeHealth(false);
      setInterval(() => this.probeHealth(false), 15000);
    },

    async probeHealth(showToast = false) {
      try {
        const res = await fetch('/api/v1/health');
        const data = await res.json().catch(() => ({ status: 'degraded' }));

        const isHealthy = res.ok && (data.status === 'healthy' || data.status === 'ok');

        // Update top-nav heartbeat
        const pill = document.getElementById('gateway-status-pill');
        const text = document.getElementById('gateway-status-text');

        if (pill && text) {
          pill.className = `status-pill ${isHealthy ? 'operational' : 'degraded'}`;
          text.textContent = isHealthy ? 'Operational' : 'Degraded';
        }

        // Update subsystem health chips
        const subsystems = data.subsystems || {};
        this.updateSubsystemChip('subsystem-status-postgres', subsystems.database || subsystems.postgres);
        this.updateSubsystemChip('subsystem-status-redis', subsystems.redis || subsystems.cache);
        this.updateSubsystemChip('subsystem-status-celery', subsystems.worker || subsystems.celery);
        this.updateSubsystemChip('subsystem-status-embedder', subsystems.model || subsystems.embedding);

        if (showToast) {
          ToastManager.show(`Health probe executed: Status ${data.status || 'healthy'}`, 'info');
        }
      } catch (err) {
        const pill = document.getElementById('gateway-status-pill');
        const text = document.getElementById('gateway-status-text');
        if (pill && text) {
          pill.className = 'status-pill offline';
          text.textContent = 'Offline';
        }
        if (showToast) {
          ToastManager.show('Health probe failed: Gateway offline', 'error');
        }
      }
    },

    updateSubsystemChip(chipId, subData) {
      const chip = document.getElementById(chipId);
      if (!chip) return;

      const isSubHealthy = !subData || subData.status === 'healthy' || subData.status === 'ok' || subData.status === 'connected' || subData === true;

      chip.className = `subsystem-status-chip ${isSubHealthy ? 'healthy' : 'degraded'}`;
      chip.textContent = isSubHealthy ? 'Healthy' : 'Degraded';
    },

    async purgeCache() {
      try {
        const res = await fetch('/api/v1/cache', { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json().catch(() => ({}));
        const count = data.purged_count !== undefined ? data.purged_count : (data.keys_purged !== undefined ? data.keys_purged : 0);

        ToastManager.show(`Search cache invalidated (${count} keys purged)`, 'success');
      } catch (err) {
        ToastManager.show(`Cache invalidation failed: ${err.message}`, 'error');
      }
    },

    async copyCurl() {
      const code = this.curlSnippetCode ? this.curlSnippetCode.textContent : '';
      if (!code) return;

      try {
        await navigator.clipboard.writeText(code);
        if (this.btnCopyCurl) {
          const oldText = this.btnCopyCurl.textContent;
          this.btnCopyCurl.textContent = 'Copied!';
          setTimeout(() => {
            if (this.btnCopyCurl) this.btnCopyCurl.textContent = oldText;
          }, 2000);
        }
        ToastManager.show('cURL command copied to clipboard', 'info', 2000);
      } catch {
        ToastManager.show('Failed to copy to clipboard', 'warning');
      }
    }
  };

  // =========================================================================
  // Global App Namespace & Initialization
  // =========================================================================

  window.StrataApp = {
    inspectContext(index) {
      SearchController.openContextModal(index);
    },

    removeStagedFile(index) {
      KnowledgeBaseController.removeStagedFile(index);
    },

    promptDelete(docId, docName) {
      KnowledgeBaseController.promptDelete(docId, docName);
    },

    filterInSearch(docId) {
      const scopeSelect = document.getElementById('scope-filter-select');
      if (scopeSelect) {
        scopeSelect.value = docId;
      }
      NavigationController.switchTab('tab-search');
      const searchInput = document.getElementById('search-query-input');
      if (searchInput) searchInput.focus();
      ToastManager.show(`Filtered search scope to document: ${docId}`, 'info', 2500);
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    ToastManager.init();
    NavigationController.init();
    SearchController.init();
    KnowledgeBaseController.init();
    TelemetryController.init();
  });

})();
