// Frontend Application State
let state = {
    targets: [],
    logs: [],
    settings: {},
    activeFilterTargetId: '',
    autoRefreshInterval: null
};

// DOM Elements Cache
const elements = {
    // Badges & Stats
    statusBadge: document.getElementById('system-status-badge'),
    statusText: document.querySelector('#system-status-badge .status-text'),
    statActiveSites: document.getElementById('stat-active-sites'),
    statTotalChecks: document.getElementById('stat-total-checks'),
    statActiveAlerts: document.getElementById('stat-active-alerts'),
    statReliability: document.getElementById('stat-reliability'),
    cardAlertDefacements: document.getElementById('card-alert-defacements'),

    // Add Target Form
    btnShowAddTarget: document.getElementById('btn-show-add-target'),
    btnCancelAdd: document.getElementById('btn-cancel-add'),
    addTargetBox: document.getElementById('add-target-box'),
    formAddTarget: document.getElementById('form-add-target'),
    targetNameInput: document.getElementById('target-name'),
    targetUrlInput: document.getElementById('target-url'),
    targetIgnoredSelectorsInput: document.getElementById('target-ignored-selectors'),
    targetSelectorsInput: document.getElementById('target-selectors'),

    // Edit Target Modal
    editTargetModal: document.getElementById('edit-target-modal'),
    btnCloseEditTarget: document.getElementById('btn-close-edit-target'),
    btnCancelEditTarget: document.getElementById('btn-cancel-edit-target'),
    formEditTarget: document.getElementById('form-edit-target'),
    editTargetIdInput: document.getElementById('edit-target-id'),
    editTargetNameInput: document.getElementById('edit-target-name'),
    editTargetUrlInput: document.getElementById('edit-target-url'),
    editTargetIgnoredSelectorsInput: document.getElementById('edit-target-ignored-selectors'),
    editTargetSelectorsInput: document.getElementById('edit-target-selectors'),

    // Lists
    targetsList: document.getElementById('targets-list'),
    logsList: document.getElementById('logs-list'),
    selectFilterTarget: document.getElementById('select-filter-target'),

    // Settings Modal
    btnSettings: document.getElementById('btn-settings'),
    btnCloseSettings: document.getElementById('btn-close-settings'),
    btnCancelSettings: document.getElementById('btn-cancel-settings'),
    settingsModal: document.getElementById('settings-modal'),
    formSettings: document.getElementById('form-settings'),

    // Inspector Modal
    inspectorModal: document.getElementById('inspector-modal'),
    btnCloseInspector: document.getElementById('btn-close-inspector'),
    inspectSite: document.getElementById('inspect-site'),
    inspectScore: document.getElementById('inspect-score'),
    inspectTime: document.getElementById('inspect-time'),
    inspectTag: document.getElementById('inspect-tag'),
    inspectSummary: document.getElementById('inspect-summary'),
    inspectorTitle: document.getElementById('inspector-title'),
    
    // Slider & Comparison Elements
    imgBaseline: document.getElementById('img-baseline'),
    imgCurrent: document.getElementById('img-current'),
    imgOverlayWrap: document.getElementById('img-overlay-wrap'),
    sliderHandle: document.getElementById('slider-handle'),
    
    // Side by Side View Elements
    sideImgBaseline: document.getElementById('side-img-baseline'),
    sideImgCurrent: document.getElementById('side-img-current'),
    sideImgDiff: document.getElementById('side-img-diff'),
    visualContainerSplit: document.getElementById('visual-container-split'),
    visualContainerSide: document.getElementById('visual-container-side')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    fetchData();
    
    // Refresh stats and logs automatically every 10 seconds
    state.autoRefreshInterval = setInterval(() => {
        fetchStats();
        fetchLogs(state.activeFilterTargetId);
    }, 10000);
});

// Event Listeners setup
function setupEventListeners() {
    // Add Target Form Toggle
    elements.btnShowAddTarget.addEventListener('click', () => {
        elements.addTargetBox.classList.toggle('expanded');
    });
    elements.btnCancelAdd.addEventListener('click', () => {
        elements.addTargetBox.classList.remove('expanded');
        elements.formAddTarget.reset();
    });

    // Add Target Submission
    elements.formAddTarget.addEventListener('submit', handleAddTarget);

    // Filter Logs
    elements.selectFilterTarget.addEventListener('change', (e) => {
        state.activeFilterTargetId = e.target.value;
        fetchLogs(state.activeFilterTargetId);
    });

    // Edit Target Modal Toggles
    elements.btnCloseEditTarget.addEventListener('click', closeEditTargetModal);
    elements.btnCancelEditTarget.addEventListener('click', closeEditTargetModal);
    elements.formEditTarget.addEventListener('submit', handleSaveTargetEdit);

    // Settings Modal Toggles
    elements.btnSettings.addEventListener('click', openSettingsModal);
    elements.btnCloseSettings.addEventListener('click', closeSettingsModal);
    elements.btnCancelSettings.addEventListener('click', closeSettingsModal);
    elements.formSettings.addEventListener('submit', handleSaveSettings);

    // Tab Switching in Settings
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // Slider Tabs (Interactive Slider vs Side-by-Side)
    const sliderTabButtons = document.querySelectorAll('.slider-tab-btn');
    sliderTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            sliderTabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            if (btn.dataset.view === 'split') {
                elements.visualContainerSplit.classList.remove('hidden');
                elements.visualContainerSide.classList.add('hidden');
                setTimeout(adjustSliderLayout, 50); // let layout render
            } else {
                elements.visualContainerSplit.classList.add('hidden');
                elements.visualContainerSide.classList.remove('hidden');
            }
        });
    });

    // Inspector Modal Close
    elements.btnCloseInspector.addEventListener('click', () => {
        elements.inspectorModal.classList.remove('active');
    });

    // Handle Slider drag interaction
    elements.sliderHandle.addEventListener('input', (e) => {
        const val = e.target.value;
        elements.imgOverlayWrap.style.width = `${val}%`;
    });

    // Window Resize -> Adjust comparison image alignment
    window.addEventListener('resize', adjustSliderLayout);
    
    // Set up initial slider align when image loads
    elements.imgBaseline.addEventListener('load', adjustSliderLayout);
}

// Adjusts the overlay image width to match the baseline image width exactly
// This prevents the sliding overlay screenshot from stretching/squeezing
function adjustSliderLayout() {
    if (elements.inspectorModal.classList.contains('active') && !elements.visualContainerSplit.classList.contains('hidden')) {
        const baselineWidth = elements.imgBaseline.clientWidth;
        elements.imgCurrent.style.width = `${baselineWidth}px`;
    }
}

// --- API Calls ---

async function fetchData() {
    await fetchStats();
    await fetchTargets();
    await fetchLogs();
}

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        // Render system health status
        if (stats.system_status === 'SECURE') {
            elements.statusBadge.className = 'status-badge secure';
            elements.statusText.textContent = 'All Systems Secure';
            elements.cardAlertDefacements.classList.remove('alert-active');
        } else {
            elements.statusBadge.className = 'status-badge alert';
            elements.statusText.textContent = 'Defacement Alert Active!';
            elements.cardAlertDefacements.classList.add('alert-active');
        }

        // Render Stats numbers
        elements.statActiveSites.textContent = `${stats.active_sites} / ${stats.total_sites}`;
        elements.statTotalChecks.textContent = stats.total_checks.toLocaleString();
        elements.statActiveAlerts.textContent = stats.active_defacements;
        elements.statReliability.textContent = `${stats.reliability_rate}%`;
    } catch (e) {
        console.error('Error fetching stats:', e);
    }
}

async function fetchTargets() {
    try {
        const response = await fetch('/api/targets');
        state.targets = await response.json();
        renderTargets();
        updateFilterOptions();
    } catch (e) {
        console.error('Error fetching targets:', e);
        elements.targetsList.innerHTML = `<div class="loading-spinner">Failed to load websites.</div>`;
    }
}

async function fetchLogs(targetId = '') {
    try {
        let url = '/api/logs?limit=50';
        if (targetId) {
            url += `&target_id=${targetId}`;
        }
        const response = await fetch(url);
        state.logs = await response.json();
        renderLogs();
    } catch (e) {
        console.error('Error fetching logs:', e);
        elements.logsList.innerHTML = `<div class="loading-spinner">Failed to load logs.</div>`;
    }
}

// --- DOM Renders ---

function renderTargets() {
    if (state.targets.length === 0) {
        elements.targetsList.innerHTML = `
            <div style="text-align: center; color: var(--text-secondary); padding: 2rem;">
                <p>No websites registered.</p>
                <p style="font-size: 0.8rem; margin-top: 0.5rem;">Click "+ Add Site" above to start auditing.</p>
            </div>
        `;
        return;
    }

    elements.targetsList.innerHTML = state.targets.map(target => {
        let statusClass = 'paused';
        let statusText = 'Paused';

        if (target.is_active) {
            statusClass = 'monitoring';
            statusText = 'Monitoring';
            
            // Check if this website has a logged defacement alert
            const siteLogs = state.logs.filter(l => l.target_id === target.id);
            if (siteLogs.length > 0 && siteLogs[0].is_defaced === 1) {
                statusClass = 'defaced';
                statusText = 'Defaced!';
            }
        }

        const ignoredBadge = target.ignored_selectors ? 
            `<div class="target-rules-badge" title="Ignored dynamic elements (clocks/tickers)">🛡️ Ignored: <code>${escapeHTML(target.ignored_selectors)}</code></div>` : '';
        const sectionBadge = target.target_selectors ? 
            `<div class="target-rules-badge focus" title="Target section focus">🎯 Focus: <code>${escapeHTML(target.target_selectors)}</code></div>` : '';

        return `
            <div class="target-item" data-id="${target.id}">
                <div class="target-info">
                    <div class="target-title-row">
                        <span class="target-name">${escapeHTML(target.name)}</span>
                        <span class="target-status-badge ${statusClass}">${statusText}</span>
                    </div>
                    <a href="${target.url}" target="_blank" class="target-url">${escapeHTML(target.url)}</a>
                    ${ignoredBadge}
                    ${sectionBadge}
                </div>
                <div class="target-meta-row">
                    <div class="target-actions">
                        <button class="btn btn-secondary btn-sm btn-toggle-active" onclick="toggleTarget(${target.id}, ${target.is_active})">
                            ${target.is_active ? '⏸️ Pause' : '▶️ Resume'}
                        </button>
                        <button class="btn btn-secondary btn-sm btn-edit-rules" title="Configure Ignored Elements" onclick="openEditTargetModal(${target.id})">
                            ⚙️ Rules
                        </button>
                        <button class="btn btn-secondary btn-sm btn-reset-baseline" title="Reset Baseline Image" onclick="resetBaseline(${target.id})">
                            🔄 Reset Base
                        </button>
                    </div>
                    <button class="btn btn-danger btn-sm btn-icon" title="Delete Website" onclick="deleteTarget(${target.id})">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderLogs() {
    if (state.logs.length === 0) {
        elements.logsList.innerHTML = `
            <div style="text-align: center; color: var(--text-secondary); padding: 3rem;">
                <p>No activity logs captured yet.</p>
                <p style="font-size: 0.85rem; margin-top: 0.5rem;">Checks run automatically every 5 minutes.</p>
            </div>
        `;
        return;
    }

    elements.logsList.innerHTML = state.logs.map(log => {
        let statusIcon = '✅';
        let itemClass = '';
        let tagClass = 'tag-no-change';
        let tagText = 'Secure';

        if (log.status === 'FAILED') {
            statusIcon = '⚠️';
            tagClass = 'tag-error';
            tagText = 'Error';
        } else if (log.is_defaced === 1) {
            statusIcon = '🚨';
            itemClass = 'defaced-alert';
            tagClass = 'tag-defaced';
            tagText = 'Defacement Alert';
        } else if (log.change_type && log.change_type !== 'No Change' && log.change_type !== 'Baseline Created') {
            statusIcon = 'ℹ️';
            tagClass = 'tag-update';
            tagText = log.change_type;
        }

        const dateFormatted = formatTimestamp(log.timestamp);
        const scoreFormatted = log.similarity_score !== null ? `${(log.similarity_score * 100).toFixed(1)}%` : 'N/A';
        const isScoreLow = log.similarity_score !== null && log.similarity_score < 0.98;

        return `
            <div class="log-item ${itemClass}" onclick="inspectLog(${log.id})">
                <div class="log-status-icon">${statusIcon}</div>
                <div class="log-details">
                    <div class="log-site-info">
                        <span class="log-site-name">${escapeHTML(log.target_name)}</span>
                        <span class="log-score-tag ${isScoreLow ? 'score-low' : ''}" title="Visual Similarity Score">Similarity: ${scoreFormatted}</span>
                    </div>
                    <div class="log-summary">${escapeHTML(log.analysis_summary || 'Manual audit or status ok.')}</div>
                </div>
                <div class="log-meta">
                    <span class="tag ${tagClass}">${tagText}</span>
                    <span class="log-time">${dateFormatted}</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateFilterOptions() {
    const currentVal = elements.selectFilterTarget.value;
    
    let html = '<option value="">All Sites</option>';
    state.targets.forEach(target => {
        html += `<option value="${target.id}">${escapeHTML(target.name)}</option>`;
    });
    elements.selectFilterTarget.innerHTML = html;
    elements.selectFilterTarget.value = currentVal;
}

// --- Action Handlers ---

async function handleAddTarget(e) {
    e.preventDefault();
    const name = elements.targetNameInput.value.trim();
    const url = elements.targetUrlInput.value.trim();
    const ignored_selectors = elements.targetIgnoredSelectorsInput ? elements.targetIgnoredSelectorsInput.value.trim() : '';
    const target_selectors = elements.targetSelectorsInput ? elements.targetSelectorsInput.value.trim() : '';

    if (!name || !url) return;

    try {
        const response = await fetch('/api/targets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url, ignored_selectors, target_selectors })
        });
        
        if (response.ok) {
            elements.addTargetBox.classList.remove('expanded');
            elements.formAddTarget.reset();
            fetchStats();
            fetchTargets();
            fetchLogs();
        } else {
            const err = await response.json();
            alert(`Error adding site: ${err.detail || 'Unknown error'}`);
        }
    } catch (err) {
        console.error(err);
        alert('Network error adding site.');
    }
}

async function toggleTarget(id, currentActive) {
    event.stopPropagation();
    try {
        const response = await fetch(`/api/targets/${id}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: !currentActive })
        });
        if (response.ok) {
            fetchTargets();
            fetchStats();
        }
    } catch (err) {
        console.error(err);
    }
}

async function resetBaseline(id) {
    event.stopPropagation();
    if (!confirm('Are you sure you want to reset the baseline? This will set the last captured screenshot as the new trusted baseline.')) {
        return;
    }
    try {
        const response = await fetch(`/api/targets/${id}/reset-baseline`, {
            method: 'POST'
        });
        const result = await response.json();
        alert(result.message);
        fetchLogs();
    } catch (err) {
        console.error(err);
        alert('Failed to reset baseline.');
    }
}

async function deleteTarget(id) {
    event.stopPropagation();
    if (!confirm('Are you sure you want to remove this website from monitoring? This deletes all history logs and screenshots.')) {
        return;
    }
    try {
        const response = await fetch(`/api/targets/${id}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            fetchTargets();
            fetchStats();
            fetchLogs();
        }
    } catch (err) {
        console.error(err);
    }
}

// Edit Target Modal functions
function openEditTargetModal(id) {
    if (event) event.stopPropagation();
    const target = state.targets.find(t => t.id === id);
    if (!target) return;

    elements.editTargetIdInput.value = target.id;
    elements.editTargetNameInput.value = target.name || '';
    elements.editTargetUrlInput.value = target.url || '';
    elements.editTargetIgnoredSelectorsInput.value = target.ignored_selectors || '';
    elements.editTargetSelectorsInput.value = target.target_selectors || '';

    elements.editTargetModal.classList.add('active');
}

function closeEditTargetModal() {
    elements.editTargetModal.classList.remove('active');
}

async function handleSaveTargetEdit(e) {
    e.preventDefault();
    const id = elements.editTargetIdInput.value;
    const name = elements.editTargetNameInput.value.trim();
    const url = elements.editTargetUrlInput.value.trim();
    const ignored_selectors = elements.editTargetIgnoredSelectorsInput.value.trim();
    const target_selectors = elements.editTargetSelectorsInput.value.trim();

    if (!id || !name || !url) return;

    try {
        const response = await fetch(`/api/targets/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url, ignored_selectors, target_selectors })
        });

        if (response.ok) {
            closeEditTargetModal();
            fetchTargets();
            fetchLogs();
            alert('Website monitoring rules updated successfully.');
        } else {
            const err = await response.json();
            alert(`Failed to update target: ${err.detail || 'Unknown error'}`);
        }
    } catch (err) {
        console.error(err);
        alert('Network error updating website rules.');
    }
}

// Settings Modal Operations
async function openSettingsModal() {
    try {
        const response = await fetch('/api/settings');
        state.settings = await response.json();
        
        // Populate inputs
        document.getElementById('check-interval').value = state.settings.check_interval_mins;
        document.getElementById('similarity-threshold').value = state.settings.similarity_threshold;
        document.getElementById('ai-provider').value = state.settings.ai_provider || 'ollama';
        document.getElementById('ollama-url').value = state.settings.ollama_url || 'http://localhost:11434';
        document.getElementById('ollama-model').value = state.settings.ollama_model || 'llama3.2-vision';
        document.getElementById('webhook-url').value = state.settings.webhook_url || '';
        document.getElementById('smtp-host').value = state.settings.smtp_host || '';
        document.getElementById('smtp-port').value = state.settings.smtp_port || '587';
        document.getElementById('smtp-user').value = state.settings.smtp_user || '';
        document.getElementById('smtp-pass').value = state.settings.smtp_password || '';
        document.getElementById('alert-email-to').value = state.settings.alert_email_to || '';
        
        elements.settingsModal.classList.add('active');
    } catch (err) {
        console.error('Error opening settings:', err);
    }
}

function closeSettingsModal() {
    elements.settingsModal.classList.remove('active');
}

async function handleSaveSettings(e) {
    e.preventDefault();
    const check_interval_mins = parseInt(document.getElementById('check-interval').value);
    const similarity_threshold = parseFloat(document.getElementById('similarity-threshold').value);
    const ai_provider = document.getElementById('ai-provider').value;
    const ollama_url = document.getElementById('ollama-url').value.trim();
    const ollama_model = document.getElementById('ollama-model').value.trim();
    const webhook_url = document.getElementById('webhook-url').value.trim();
    const smtp_host = document.getElementById('smtp-host').value.trim();
    const smtp_port = parseInt(document.getElementById('smtp-port').value) || 587;
    const smtp_user = document.getElementById('smtp-user').value.trim();
    const smtp_password = document.getElementById('smtp-pass').value;
    const alert_email_to = document.getElementById('alert-email-to').value.trim();

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                check_interval_mins,
                similarity_threshold,
                ai_provider,
                ollama_url,
                ollama_model,
                webhook_url,
                smtp_host,
                smtp_port,
                smtp_user,
                smtp_password,
                alert_email_to
            })
        });

        if (response.ok) {
            closeSettingsModal();
            fetchLogs();
            alert('Settings updated successfully.');
        } else {
            alert('Failed to save settings.');
        }
    } catch (err) {
        console.error(err);
        alert('Network error saving settings.');
    }
}

// Inspector Modal (Audit view)
function inspectLog(logId) {
    const log = state.logs.find(l => l.id === logId);
    if (!log) return;
    
    // Setup labels and texts
    elements.inspectSite.textContent = log.target_name;
    elements.inspectScore.textContent = log.similarity_score !== null ? `${(log.similarity_score * 100).toFixed(2)}%` : 'N/A';
    elements.inspectTime.textContent = formatTimestamp(log.timestamp);
    
    // Tag styling
    let tagText = 'Secure';
    let tagClass = 'tag-no-change';
    if (log.status === 'FAILED') {
        tagText = 'Error';
        tagClass = 'tag-error';
    } else if (log.is_defaced === 1) {
        tagText = `Defacement Alert (${log.confidence}% Confidence)`;
        tagClass = 'tag-defaced';
    } else if (log.change_type && log.change_type !== 'No Change') {
        tagText = log.change_type;
        tagClass = 'tag-update';
    }
    
    elements.inspectTag.className = `tag ${tagClass}`;
    elements.inspectTag.textContent = tagText;
    elements.inspectSummary.textContent = log.analysis_summary || 'No changes detected. Website looks normal.';
    
    // Setup screenshots URLs
    // Baseline path is under: static/screenshots/{target_id}/baseline.png
    const baselineUrl = `/static/screenshots/${log.target_id}/baseline.png`;
    const currentUrl = log.screenshot_path || '/static/screenshots/placeholder.png';
    const diffUrl = log.diff_path || '/static/screenshots/placeholder.png';
    
    // Load images
    elements.imgBaseline.src = baselineUrl;
    elements.imgCurrent.src = currentUrl;
    
    // Side by side images
    elements.sideImgBaseline.src = baselineUrl;
    elements.sideImgCurrent.src = currentUrl;
    elements.sideImgDiff.src = diffUrl;

    // Reset slider to 50%
    elements.sliderHandle.value = 50;
    elements.imgOverlayWrap.style.width = '50%';
    
    // Show modal
    elements.inspectorModal.classList.add('active');
    
    // Trigger alignment check once images load
    setTimeout(adjustSliderLayout, 100);
}

// --- Utility Functions ---

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

function formatTimestamp(timestampStr) {
    if (!timestampStr) return '';
    try {
        const d = new Date(timestampStr);
        return d.toLocaleString();
    } catch (e) {
        return timestampStr;
    }
}
