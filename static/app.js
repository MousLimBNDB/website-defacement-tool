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

    // Edit Target Modal
    editTargetModal: document.getElementById('edit-target-modal'),
    btnCloseEditTarget: document.getElementById('btn-close-edit-target'),
    btnCancelEditTarget: document.getElementById('btn-cancel-edit-target'),
    formEditTarget: document.getElementById('form-edit-target'),
    editTargetIdInput: document.getElementById('edit-target-id'),
    editTargetNameInput: document.getElementById('edit-target-name'),
    editTargetUrlInput: document.getElementById('edit-target-url'),

    // Lists & Dropdowns
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

    const btnTestWebhook = document.getElementById('btn-test-webhook');
    if (btnTestWebhook) {
        btnTestWebhook.addEventListener('click', handleTestWebhook);
    }

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
                setTimeout(adjustSliderLayout, 50);
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

    // Slider Drag Control
    elements.sliderHandle.addEventListener('input', (e) => {
        const val = e.target.value;
        elements.imgOverlayWrap.style.width = `${val}%`;
    });
}

// Fetch Initial State Data
async function fetchData() {
    await Promise.all([
        fetchTargets(),
        fetchStats(),
        fetchLogs()
    ]);
}

// Target API Calls
async function fetchTargets() {
    try {
        const res = await fetch('/api/targets');
        state.targets = await res.json();
        renderTargets();
        updateTargetFilterDropdown();
    } catch (e) {
        console.error('Failed to fetch targets:', e);
    }
}

async function handleAddTarget(e) {
    e.preventDefault();
    const name = elements.targetNameInput.value.trim();
    const url = elements.targetUrlInput.value.trim();

    if (!name || !url) return;

    try {
        const res = await fetch('/api/targets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url })
        });

        if (res.ok) {
            elements.formAddTarget.reset();
            elements.addTargetBox.classList.remove('expanded');
            fetchTargets();
            fetchStats();
        } else {
            const data = await res.json();
            alert(`Error adding target: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        console.error('Error adding target:', err);
    }
}

function openEditTargetModal(targetId) {
    const target = state.targets.find(t => t.id === targetId);
    if (!target) return;

    elements.editTargetIdInput.value = target.id;
    elements.editTargetNameInput.value = target.name;
    elements.editTargetUrlInput.value = target.url;

    elements.editTargetModal.classList.add('active');
}

function closeEditTargetModal() {
    elements.editTargetModal.classList.remove('active');
    elements.formEditTarget.reset();
}

async function handleSaveTargetEdit(e) {
    e.preventDefault();
    const targetId = elements.editTargetIdInput.value;
    const name = elements.editTargetNameInput.value.trim();
    const url = elements.editTargetUrlInput.value.trim();

    try {
        const res = await fetch(`/api/targets/${targetId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url })
        });

        if (res.ok) {
            closeEditTargetModal();
            fetchTargets();
        } else {
            alert('Failed to update target rules.');
        }
    } catch (err) {
        console.error('Error updating target:', err);
    }
}

async function toggleTargetStatus(targetId, currentStatus) {
    try {
        const res = await fetch(`/api/targets/${targetId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: !currentStatus })
        });

        if (res.ok) {
            fetchTargets();
            fetchStats();
        }
    } catch (err) {
        console.error('Failed to toggle target status:', err);
    }
}

async function resetTargetBaseline(targetId) {
    if (!confirm('Re-establish current snapshot as the clean baseline?')) return;

    try {
        const res = await fetch(`/api/targets/${targetId}/reset-baseline`, {
            method: 'POST'
        });

        const data = await res.json();
        alert(data.message || 'Baseline reset completed.');
        fetchLogs();
    } catch (err) {
        console.error('Failed to reset baseline:', err);
    }
}

async function deleteTarget(targetId) {
    if (!confirm('Are you sure you want to delete this target and all its logs?')) return;

    try {
        const res = await fetch(`/api/targets/${targetId}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            fetchTargets();
            fetchStats();
            fetchLogs();
        }
    } catch (err) {
        console.error('Failed to delete target:', err);
    }
}

// Render Targets List
function renderTargets() {
    if (state.targets.length === 0) {
        elements.targetsList.innerHTML = `
            <div class="empty-state">
                <p>No website targets monitored.</p>
                <button onclick="document.getElementById('btn-show-add-target').click()" class="btn btn-secondary btn-sm" style="margin-top:0.5rem;">+ Add Your First Website</button>
            </div>
        `;
        return;
    }

    elements.targetsList.innerHTML = state.targets.map(t => `
        <div class="target-card ${t.is_active ? '' : 'inactive'}">
            <div class="target-main">
                <div class="target-info">
                    <h4>${escapeHtml(t.name)}</h4>
                    <a href="${escapeHtml(t.url)}" target="_blank" class="target-url">${escapeHtml(t.url)}</a>
                </div>
                <div class="target-toggle">
                    <label class="switch">
                        <input type="checkbox" ${t.is_active ? 'checked' : ''} onchange="toggleTargetStatus(${t.id}, ${t.is_active})">
                        <span class="slider round"></span>
                    </label>
                </div>
            </div>
            <div class="target-actions">
                <button class="btn-action" onclick="resetTargetBaseline(${t.id})" title="Reset Baseline Image">🎯 Reset Baseline</button>
                <button class="btn-action" onclick="openEditTargetModal(${t.id})" title="Edit Rules">⚙️ Edit</button>
                <button class="btn-action danger" onclick="deleteTarget(${t.id})" title="Delete Target">🗑️ Delete</button>
            </div>
        </div>
    `).join('');
}

function updateTargetFilterDropdown() {
    const currentVal = elements.selectFilterTarget.value;
    elements.selectFilterTarget.innerHTML = `
        <option value="">All Monitored Sites</option>
        ${state.targets.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('')}
    `;
    elements.selectFilterTarget.value = currentVal;
}

// Stats API Calls
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();

        elements.statActiveSites.textContent = `${stats.active_sites} / ${stats.total_sites}`;
        elements.statTotalChecks.textContent = stats.total_checks;
        elements.statActiveAlerts.textContent = stats.active_defacements;
        elements.statReliability.textContent = `${stats.reliability_rate}%`;

        if (stats.active_defacements > 0) {
            elements.statusBadge.className = 'status-badge alert';
            elements.statusText.textContent = `${stats.active_defacements} DEFACEMENT ALERT(S)`;
            elements.cardAlertDefacements.classList.add('active-alert');
        } else {
            elements.statusBadge.className = 'status-badge secure';
            elements.statusText.textContent = 'All Systems Secure';
            elements.cardAlertDefacements.classList.remove('active-alert');
        }
    } catch (e) {
        console.error('Failed to fetch stats:', e);
    }
}

// Logs API Calls
async function fetchLogs(targetId = '') {
    try {
        const url = targetId ? `/api/logs?target_id=${targetId}&limit=50` : '/api/logs?limit=50';
        const res = await fetch(url);
        state.logs = await res.json();
        renderLogs();
    } catch (e) {
        console.error('Failed to fetch logs:', e);
    }
}

// Render Logs Feed
function renderLogs() {
    if (state.logs.length === 0) {
        elements.logsList.innerHTML = `<div class="empty-state"><p>No audit activity recorded yet.</p></div>`;
        return;
    }

    elements.logsList.innerHTML = state.logs.map(log => {
        let badgeClass = 'tag-secure';
        let tagText = 'NORMAL';

        if (log.status === 'FAILED') {
            badgeClass = 'tag-error';
            tagText = 'ERROR';
        } else if (log.is_defaced === 1) {
            badgeClass = 'tag-defaced';
            tagText = `DEFACEMENT (${log.confidence}%)`;
        } else if (log.change_type === 'Baseline Created' || log.change_type === 'Baseline Reset') {
            badgeClass = 'tag-baseline';
            tagText = log.change_type.toUpperCase();
        } else if (log.similarity_score < 0.98) {
            badgeClass = 'tag-update';
            tagText = log.change_type || 'UPDATE';
        }

        const formattedTime = new Date(log.timestamp).toLocaleString();
        const scorePercent = log.similarity_score ? (log.similarity_score * 100).toFixed(1) : '0.0';

        return `
            <div class="log-card ${log.is_defaced === 1 ? 'log-defaced' : ''}">
                <div class="log-header">
                    <div class="log-site-info">
                        <strong>${escapeHtml(log.target_name || 'Website')}</strong>
                        <span class="log-time">${formattedTime}</span>
                    </div>
                    <span class="tag ${badgeClass}">${tagText}</span>
                </div>
                <div class="log-body">
                    <p class="log-summary">${escapeHtml(log.analysis_summary || log.error_message || 'Audit check completed.')}</p>
                    <div class="log-meta">
                        <span>Similarity Score: <strong>${scorePercent}%</strong></span>
                        ${log.screenshot_path ? `<button class="btn-inspect" onclick="openInspectorModal(${log.id})">🔍 Inspect Visual Comparison</button>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Inspector Modal Handler
function openInspectorModal(logId) {
    const log = state.logs.find(l => l.id === logId);
    if (!log || !log.screenshot_path) return;

    elements.inspectSite.textContent = log.target_name || log.target_url;
    elements.inspectScore.textContent = `${(log.similarity_score * 100).toFixed(2)}%`;
    elements.inspectTime.textContent = new Date(log.timestamp).toLocaleString();
    elements.inspectSummary.textContent = log.analysis_summary || 'No diagnostic summary provided.';

    if (log.is_defaced === 1) {
        elements.inspectTag.className = 'tag tag-defaced';
        elements.inspectTag.textContent = `DEFACEMENT (${log.confidence}% confidence)`;
    } else {
        elements.inspectTag.className = 'tag tag-secure';
        elements.inspectTag.textContent = log.change_type || 'NORMAL INTEGRITY';
    }

    const targetId = log.target_id;
    const baselineUrl = `/static/screenshots/${targetId}/baseline.png`;
    const currentUrl = log.screenshot_path;
    const diffUrl = log.diff_path || log.screenshot_path;

    elements.imgBaseline.src = baselineUrl;
    elements.imgCurrent.src = currentUrl;

    elements.sideImgBaseline.src = baselineUrl;
    elements.sideImgCurrent.src = currentUrl;
    elements.sideImgDiff.src = diffUrl;

    elements.sliderHandle.value = 50;
    elements.imgOverlayWrap.style.width = '50%';

    elements.inspectorModal.classList.add('active');
    setTimeout(adjustSliderLayout, 100);
}

function adjustSliderLayout() {
    if (elements.imgBaseline.complete && elements.imgBaseline.naturalWidth > 0) {
        elements.imgCurrent.style.width = `${elements.imgBaseline.clientWidth}px`;
    } else {
        elements.imgBaseline.onload = () => {
            elements.imgCurrent.style.width = `${elements.imgBaseline.clientWidth}px`;
        };
    }
}

// Settings Modal Handler
async function openSettingsModal() {
    try {
        const res = await fetch('/api/settings');
        state.settings = await res.json();

        document.getElementById('check-interval').value = state.settings.check_interval || state.settings.check_interval_mins || 5;
        document.getElementById('check-interval-unit').value = state.settings.check_interval_unit || 'minutes';
        document.getElementById('similarity-threshold').value = state.settings.similarity_threshold || 0.98;
        document.getElementById('browser-engine').value = state.settings.browser_engine || 'firefox';

        const useLlm = String(state.settings.use_llm || 'true').toLowerCase() !== 'false';
        document.getElementById('use-llm').checked = useLlm;
        document.getElementById('ollama-url').value = state.settings.ollama_url || 'http://localhost:11434';
        document.getElementById('ollama-model').value = state.settings.ollama_model || 'llama3.2-vision';

        document.getElementById('webhook-url').value = state.settings.webhook_url || '';
        document.getElementById('webhook-trigger-on').value = state.settings.webhook_trigger_on || 'defacement';
        document.getElementById('webhook-payload-format').value = state.settings.webhook_payload_format || 'n8n';

        const testResBox = document.getElementById('webhook-test-result');
        if (testResBox) testResBox.style.display = 'none';

        elements.settingsModal.classList.add('active');
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

function closeSettingsModal() {
    elements.settingsModal.classList.remove('active');
}

async function handleSaveSettings(e) {
    e.preventDefault();

    const payload = {
        check_interval: parseFloat(document.getElementById('check-interval').value),
        check_interval_unit: document.getElementById('check-interval-unit').value,
        similarity_threshold: parseFloat(document.getElementById('similarity-threshold').value),
        browser_engine: document.getElementById('browser-engine').value,
        use_llm: document.getElementById('use-llm').checked,
        ollama_url: document.getElementById('ollama-url').value.trim(),
        ollama_model: document.getElementById('ollama-model').value.trim(),
        webhook_url: document.getElementById('webhook-url').value.trim(),
        webhook_trigger_on: document.getElementById('webhook-trigger-on').value,
        webhook_payload_format: document.getElementById('webhook-payload-format').value
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeSettingsModal();
            alert('Settings updated successfully.');
        } else {
            alert('Failed to save settings.');
        }
    } catch (err) {
        console.error('Error saving settings:', err);
    }
}

async function handleTestWebhook() {
    const webhookUrl = document.getElementById('webhook-url').value.trim();
    const payloadFormat = document.getElementById('webhook-payload-format').value;
    const resultBox = document.getElementById('webhook-test-result');

    if (!webhookUrl) {
        alert('Please enter a Webhook Endpoint URL first.');
        return;
    }

    resultBox.style.display = 'block';
    resultBox.style.background = 'rgba(59, 130, 246, 0.15)';
    resultBox.style.border = '1px solid rgba(59, 130, 246, 0.3)';
    resultBox.style.color = '#93c5fd';
    resultBox.textContent = '⏳ Sending test payload to n8n webhook...';

    try {
        const res = await fetch('/api/test-webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ webhook_url: webhookUrl, webhook_payload_format: payloadFormat })
        });

        const data = await res.json();
        if (res.ok) {
            resultBox.style.background = 'rgba(16, 185, 129, 0.15)';
            resultBox.style.border = '1px solid rgba(16, 185, 129, 0.3)';
            resultBox.style.color = '#6ee7b7';
            resultBox.textContent = `✅ ${data.message || 'Webhook delivered successfully!'}`;
        } else {
            resultBox.style.background = 'rgba(239, 68, 68, 0.15)';
            resultBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
            resultBox.style.color = '#fca5a5';
            resultBox.textContent = `❌ ${data.detail || 'Failed to deliver webhook payload.'}`;
        }
    } catch (err) {
        resultBox.style.background = 'rgba(239, 68, 68, 0.15)';
        resultBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        resultBox.style.color = '#fca5a5';
        resultBox.textContent = `❌ Network Error: ${err.message}`;
    }
}

// Utility Helpers
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
