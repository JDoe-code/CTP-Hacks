// Simplify Data Cleaning Web Application Frontend Script

document.addEventListener('DOMContentLoaded', () => {
    // --- Index Page Logic ---
    const uploadForm = document.getElementById('upload');
    if (uploadForm) {
        initIndexPage(uploadForm);
    }

    // --- Comparison Page Logic ---
    const beforeTable = document.getElementById('beforeTable');
    if (beforeTable) {
        initComparisonPage();
    }

    // --- Visualization Page Logic ---
    const vizContainer = document.getElementById('visualization');
    if (vizContainer) {
        initVisualizationPage();
    }
});

/**
 * Handles Form Submission and API Communication on index.html
 */
function initIndexPage(form) {
    const fileInput = document.getElementById('input');
    const rawTextInput = document.getElementById('rawText');
    const promptInput = document.getElementById('prompt');
    const optionSelect = document.getElementById('option');
    const missingSelect = document.getElementById('missingStrategy');
    const submitBtn = document.getElementById('submit');
    const loadIndicator = document.getElementById('load');
    const errorBanner = document.getElementById('error-message');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Clear previous error
        if (errorBanner) {
            errorBanner.textContent = '';
            errorBanner.classList.add('hidden');
        }

        const file = fileInput.files && fileInput.files[0];
        const rawText = rawTextInput ? rawTextInput.value.trim() : '';

        if (!file && !rawText) {
            showError('Please upload a file or paste raw data before submitting.');
            return;
        }

        // Show loading spinner
        if (loadIndicator) {
            loadIndicator.classList.remove('hidden');
        }
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing Data...';
        }

        const formData = new FormData();
        if (file) {
            formData.append('dataset', file);
        }
        if (rawText) {
            formData.append('raw_text', rawText);
        }
        if (promptInput) {
            formData.append('prompt', promptInput.value.trim());
        }
        if (optionSelect) {
            formData.append('output_format', optionSelect.value);
        }
        if (missingSelect) {
            formData.append('missing_strategy', missingSelect.value);
        }
        formData.append('ajax', 'true');

        try {
            const response = await fetch('/clean', {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || `Server error: ${response.status}`);
            }

            // Save result in sessionStorage
            sessionStorage.setItem('simplify_clean_result', JSON.stringify(data));

            // Redirect to comparison page
            window.location.href = 'comparison.html';
        } catch (err) {
            console.error('Error cleaning dataset:', err);
            showError(err.message || 'An unexpected error occurred while communicating with the Gemini backend.');
        } finally {
            if (loadIndicator) {
                loadIndicator.classList.add('hidden');
            }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Clean Data with Gemini';
            }
        }
    });

    function showError(msg) {
        if (errorBanner) {
            errorBanner.textContent = msg;
            errorBanner.classList.remove('hidden');
            errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            alert(msg);
        }
    }
}

/**
 * Initializes and Renders Comparison Page
 */
function initComparisonPage() {
    let result = null;

    // Check server injected JSON first
    const serverDataScript = document.getElementById('server-data');
    if (serverDataScript) {
        try {
            const parsed = JSON.parse(serverDataScript.textContent.trim());
            if (parsed && (parsed.before_data || parsed.preview_data || parsed.file_base64)) {
                result = parsed;
            }
        } catch (e) {
            console.log('No valid server-side JSON data found');
        }
    }

    // Fallback to sessionStorage
    if (!result) {
        const stored = sessionStorage.getItem('simplify_clean_result');
        if (stored) {
            try {
                result = JSON.parse(stored);
            } catch (e) {
                console.error('Error parsing stored clean result:', e);
            }
        }
    }

    const noDataState = document.getElementById('noDataState');
    const mainContent = document.getElementById('mainComparisonContent');

    if (!result || (!result.before_data && !result.preview_data)) {
        if (noDataState) noDataState.classList.remove('hidden');
        if (mainContent) mainContent.classList.add('hidden');
        return;
    }

    if (noDataState) noDataState.classList.add('hidden');
    if (mainContent) mainContent.classList.remove('hidden');

    renderComparisonData(result);
}

/**
 * Renders all components of the comparison page
 */
function renderComparisonData(data) {
    const beforeData = data.before_data || [];
    const afterData = data.preview_data || data.cleaned_data || [];
    const beforeCols = data.before_columns || (beforeData.length ? Object.keys(beforeData[0]) : []);
    const afterCols = data.after_columns || (afterData.length ? Object.keys(afterData[0]) : beforeCols);
    const steps = data.steps || [];
    const issues = data.issues_found || [];
    const warnings = data.warnings || [];

    // --- KPI Metrics ---
    const beforeRowCountEl = document.getElementById('beforeRowCount');
    const afterRowCountEl = document.getElementById('afterRowCount');
    const issuesCountEl = document.getElementById('issuesCount');
    const stepsCountEl = document.getElementById('stepsCount');
    const formatBadgeEl = document.getElementById('outputFormatBadge');

    const totalBefore = data.total_before_rows || beforeData.length;
    const totalAfter = data.total_after_rows || afterData.length;

    if (beforeRowCountEl) beforeRowCountEl.textContent = `${totalBefore} rows`;
    if (afterRowCountEl) afterRowCountEl.textContent = `${totalAfter} rows`;
    if (issuesCountEl) issuesCountEl.textContent = `${issues.length}`;
    if (stepsCountEl) stepsCountEl.textContent = `${steps.length}`;
    if (formatBadgeEl) formatBadgeEl.textContent = `.${data.extension || 'csv'}`;

    // --- Issues Section ---
    const issuesListEl = document.getElementById('issuesList');
    const issuesTitleCount = document.getElementById('issuesTitleCount');
    if (issuesTitleCount) issuesTitleCount.textContent = issues.length;

    if (issuesListEl) {
        issuesListEl.innerHTML = '';
        if (issues.length === 0) {
            issuesListEl.innerHTML = '<li class="no-issue">✓ No data issues detected! The dataset is clean.</li>';
        } else {
            issues.forEach(issue => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="issue-bullet">●</span> <span>${escapeHtml(issue)}</span>`;
                issuesListEl.appendChild(li);
            });
        }
    }

    // --- Steps Section ---
    const stepsListEl = document.getElementById('stepsList');
    const stepsTitleCount = document.getElementById('stepsTitleCount');
    if (stepsTitleCount) stepsTitleCount.textContent = steps.length;

    if (stepsListEl) {
        stepsListEl.innerHTML = '';
        if (steps.length === 0) {
            stepsListEl.innerHTML = '<p class="empty-hint">No cleaning steps recorded.</p>';
        } else {
            steps.forEach((step, idx) => {
                const stepNum = step.step_number || (idx + 1);
                const action = step.action || 'Data Cleaning Step';
                const col = step.column ? `<span class="col-pill">Column: ${escapeHtml(step.column)}</span>` : '';
                const details = step.details || '';

                const card = document.createElement('div');
                card.className = 'step-item';
                card.innerHTML = `
                    <div class="step-badge">Step ${stepNum}</div>
                    <div class="step-body">
                        <div class="step-header">
                            <span class="step-action">${escapeHtml(action)}</span>
                            ${col}
                        </div>
                        ${details ? `<div class="step-details">${escapeHtml(details)}</div>` : ''}
                    </div>
                `;
                stepsListEl.appendChild(card);
            });
        }
    }

    // --- Warnings Section ---
    const warningsBanner = document.getElementById('warningsBanner');
    const warningsList = document.getElementById('warningsList');
    if (warnings && warnings.length > 0 && warningsBanner && warningsList) {
        warningsList.innerHTML = '';
        warnings.forEach(w => {
            const li = document.createElement('li');
            li.textContent = w;
            warningsList.appendChild(li);
        });
        warningsBanner.classList.remove('hidden');
    } else if (warningsBanner) {
        warningsBanner.classList.add('hidden');
    }

    // --- Tables Rendering ---
    const beforeTableHead = document.getElementById('beforeTableHead');
    const beforeTableBody = document.getElementById('beforeTableBody');
    const beforeTableBadge = document.getElementById('beforeTableBadge');

    const afterTableHead = document.getElementById('afterTableHead');
    const afterTableBody = document.getElementById('afterTableBody');
    const afterTableBadge = document.getElementById('afterTableBadge');

    if (beforeTableBadge) beforeTableBadge.textContent = `${beforeData.length} preview rows`;
    if (afterTableBadge) afterTableBadge.textContent = `${afterData.length} preview rows`;

    renderTable(beforeTableHead, beforeTableBody, beforeCols, beforeData, false);
    renderTable(afterTableHead, afterTableBody, afterCols, afterData, true, beforeData);

    // --- View Toggle Controls ---
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    const grid = document.getElementById('comparisonGrid');

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const view = btn.getAttribute('data-view');
            if (grid) {
                grid.classList.remove('side-by-side', 'before-only', 'after-only');
                grid.classList.add(view);
            }
        });
    });

    // --- Download Cleaned File Button ---
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            downloadCleanedFile(data);
        });
    }
}

/**
 * Builds HTML table headers and rows
 */
function renderTable(headEl, bodyEl, columns, rows, isAfter = false, beforeRows = []) {
    if (!headEl || !bodyEl) return;

    headEl.innerHTML = '';
    bodyEl.innerHTML = '';

    if (!columns || columns.length === 0) {
        headEl.innerHTML = '<tr><th>No Columns</th></tr>';
        bodyEl.innerHTML = '<tr><td class="empty-cell">No records to display</td></tr>';
        return;
    }

    // Header row
    const trHead = document.createElement('tr');
    const thIndex = document.createElement('th');
    thIndex.textContent = '#';
    thIndex.className = 'col-index';
    trHead.appendChild(thIndex);

    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        trHead.appendChild(th);
    });
    headEl.appendChild(trHead);

    // Body rows
    if (!rows || rows.length === 0) {
        const trEmpty = document.createElement('tr');
        const tdEmpty = document.createElement('td');
        tdEmpty.colSpan = columns.length + 1;
        tdEmpty.className = 'empty-cell';
        tdEmpty.textContent = 'No records in preview';
        trEmpty.appendChild(tdEmpty);
        bodyEl.appendChild(trEmpty);
        return;
    }

    rows.forEach((row, rIdx) => {
        const tr = document.createElement('tr');
        const tdIdx = document.createElement('td');
        tdIdx.textContent = (rIdx + 1).toString();
        tdIdx.className = 'row-index';
        tr.appendChild(tdIdx);

        columns.forEach(col => {
            const td = document.createElement('td');
            const val = (row[col] !== undefined && row[col] !== null) ? row[col] : '';
            td.textContent = val;

            // Highlight difference in after table
            if (isAfter && beforeRows && beforeRows[rIdx]) {
                const beforeVal = (beforeRows[rIdx][col] !== undefined && beforeRows[rIdx][col] !== null) ? beforeRows[rIdx][col] : '';
                if (String(val).trim() !== String(beforeVal).trim()) {
                    td.classList.add('cell-changed');
                    td.title = `Original: "${beforeVal}" → Cleaned: "${val}"`;
                }
            } else if (!isAfter) {
                // Highlight empty/NA in before table
                const strVal = String(val).trim().toLowerCase();
                if (strVal === '' || strVal === 'n/a' || strVal === 'nan' || strVal === 'null' || strVal === 'tbd') {
                    td.classList.add('cell-missing');
                }
            }

            tr.appendChild(td);
        });

        bodyEl.appendChild(tr);
    });
}

/**
 * Downloads cleaned file from Base64 data
 */
function downloadCleanedFile(data) {
    if (!data.file_base64) {
        alert('No downloadable file data found in this result.');
        return;
    }

    const filename = data.filename || `cleaned_data.${data.extension || 'csv'}`;
    const mimeType = data.mime_type || 'application/octet-stream';

    try {
        const byteCharacters = atob(data.file_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: mimeType });

        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    } catch (e) {
        console.error('Download failed:', e);
        // Fallback POST form download
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/download';

        const base64Input = document.createElement('input');
        base64Input.type = 'hidden';
        base64Input.name = 'file_base64';
        base64Input.value = data.file_base64;
        form.appendChild(base64Input);

        const nameInput = document.createElement('input');
        nameInput.type = 'hidden';
        nameInput.name = 'filename';
        nameInput.value = filename;
        form.appendChild(nameInput);

        const mimeInput = document.createElement('input');
        mimeInput.type = 'hidden';
        mimeInput.name = 'mime_type';
        mimeInput.value = mimeType;
        form.appendChild(mimeInput);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }
}

/**
 * Utility: HTML Escape string
 */
function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Initializes and Renders Visualization Page
 */
function initVisualizationPage() {
    const vizEmptyState = document.getElementById('vizEmptyState');
    const vizContent = document.getElementById('vizContent');
    const vizMetrics = document.getElementById('vizMetrics');
    const vizCharts = document.getElementById('vizCharts');

    const stored = sessionStorage.getItem('simplify_clean_result');
    if (!stored) {
        if (vizEmptyState) vizEmptyState.classList.remove('hidden');
        if (vizContent) vizContent.classList.add('hidden');
        return;
    }

    try {
        const data = JSON.parse(stored);
        if (!data || (!data.before_data && !data.preview_data)) {
            if (vizEmptyState) vizEmptyState.classList.remove('hidden');
            if (vizContent) vizContent.classList.add('hidden');
            return;
        }

        if (vizEmptyState) vizEmptyState.classList.add('hidden');
        if (vizContent) vizContent.classList.remove('hidden');

        const beforeRows = data.before_data || [];
        const afterRows = data.preview_data || data.cleaned_data || [];
        const steps = data.steps || [];
        const issues = data.issues_found || [];

        if (vizMetrics) {
            vizMetrics.innerHTML = `
                <div class="metric-card">
                    <div class="metric-label">Original Rows</div>
                    <div class="metric-value">${data.total_before_rows || beforeRows.length}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Cleaned Rows</div>
                    <div class="metric-value metric-success">${data.total_after_rows || afterRows.length}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Issues Resolved</div>
                    <div class="metric-value metric-warning">${issues.length}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Steps Applied</div>
                    <div class="metric-value metric-info">${steps.length}</div>
                </div>
            `;
        }

        if (vizCharts) {
            vizCharts.innerHTML = `
                <h2>Dataset Cleaning Breakdown</h2>
                <div style="margin-top: 15px; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                    <div style="background: #f8fafc; padding: 18px; border-radius: 8px; border: 1px solid #e2e8f0;">
                        <h4 style="margin: 0 0 10px 0; color: #2d3748;">Data Retention</h4>
                        <div style="height: 14px; background: #e2e8f0; border-radius: 7px; overflow: hidden; margin-bottom: 8px;">
                            <div style="width: ${Math.min(100, Math.round(((data.total_after_rows || afterRows.length) / Math.max(1, (data.total_before_rows || beforeRows.length))) * 100))}%; height: 100%; background: #38a169;"></div>
                        </div>
                        <span style="font-size: 13px; color: #718096;">
                            ${data.total_after_rows || afterRows.length} of ${data.total_before_rows || beforeRows.length} rows retained (${Math.min(100, Math.round(((data.total_after_rows || afterRows.length) / Math.max(1, (data.total_before_rows || beforeRows.length))) * 100))}%)
                        </span>
                    </div>

                    <div style="background: #f8fafc; padding: 18px; border-radius: 8px; border: 1px solid #e2e8f0;">
                        <h4 style="margin: 0 0 10px 0; color: #2d3748;">Columns Cleaned</h4>
                        <span style="font-size: 24px; font-weight: bold; color: #3182ce;">
                            ${(data.after_columns || []).length || (data.before_columns || []).length || 0}
                        </span>
                        <p style="font-size: 13px; color: #718096; margin: 4px 0 0 0;">
                            Schema preserved and standardized across all fields
                        </p>
                    </div>
                </div>
            `;
        }
    } catch (e) {
        console.error('Failed to parse visualization data:', e);
    }
}

