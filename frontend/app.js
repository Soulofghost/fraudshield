const API_BASE = window.location.origin;

// Preloaded Threat Scenarios
const SCENARIOS = {
  coffee: {
    user_id: "usr_alvin_884",
    card_last4: "8821",
    amount: 4.85,
    merchant_name: "Blue Bottle Coffee SF",
    merchant_cat: "coffee_shop",
    lat: 37.7749,
    lon: -122.4194,
    device: "ios_alvin_device"
  },
  travel: {
    user_id: "usr_alvin_884",
    card_last4: "8821",
    amount: 1450.00,
    merchant_name: "Bic Camera Tokyo Ginza",
    merchant_cat: "luxury_jewelry",
    lat: 35.6762,
    lon: 139.6503,
    device: "unrecognized_pos_terminal"
  },
  velocity: {
    user_id: "usr_alvin_884",
    card_last4: "8821",
    amount: 12.00,
    merchant_name: "Digital Steam Key Vendor",
    merchant_cat: "digital_goods",
    lat: 37.7749,
    lon: -122.4194,
    device: "ios_alvin_device"
  },
  crypto: {
    user_id: "usr_alvin_884",
    card_last4: "8821",
    amount: 8500.00,
    merchant_name: "Binance Offshore Remittance",
    merchant_cat: "cryptocurrency_exchange",
    lat: 22.3193,
    lon: 114.1694,
    device: "tor_exit_node_proxy"
  }
};

// DOM Elements
const kpiTotal = document.getElementById("kpi-total");
const kpiRate = document.getElementById("kpi-rate");
const kpiVolume = document.getElementById("kpi-volume");
const kpiAlerts = document.getElementById("kpi-alerts");

const evalForm = document.getElementById("eval-form");
const userIdInput = document.getElementById("user-id");
const cardLast4Input = document.getElementById("card-last4");
const amountInput = document.getElementById("tx-amount");
const merchantNameInput = document.getElementById("merchant-name");
const merchantCatInput = document.getElementById("merchant-cat");
const deviceIdInput = document.getElementById("device-id");
const latInput = document.getElementById("geo-lat");
const lonInput = document.getElementById("geo-lon");

const evalResultBox = document.getElementById("eval-result-box");
const resDecisionBadge = document.getElementById("res-decision-badge");
const resScoreNum = document.getElementById("res-score-num");
const resFactorsList = document.getElementById("res-factors-list");

const alertCountPill = document.getElementById("alert-count-pill");
const alertsStream = document.getElementById("alerts-stream");
const txTbody = document.getElementById("tx-tbody");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadAnalytics();
  loadTransactions();
  loadAlerts();
});

function setupEventListeners() {
  // Scenario Chips
  document.querySelectorAll(".btn-scenario").forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.scenario;
      if (SCENARIOS[key]) {
        const s = SCENARIOS[key];
        userIdInput.value = s.user_id;
        cardLast4Input.value = s.card_last4;
        amountInput.value = s.amount;
        merchantNameInput.value = s.merchant_name;
        merchantCatInput.value = s.merchant_cat;
        latInput.value = s.lat;
        lonInput.value = s.lon;
        deviceIdInput.value = s.device;
      }
    });
  });

  evalForm.addEventListener("submit", handleEvalSubmit);

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.dataset.tab;
      document.getElementById(targetId).classList.add("active");
    });
  });
}

async function loadAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/risk-summary`);
    if (!res.ok) return;
    const data = await res.json();
    kpiTotal.textContent = data.total_transactions.toLocaleString();
    kpiRate.textContent = `${data.block_rate_percentage}%`;
    kpiVolume.textContent = `$${data.total_flagged_volume.toLocaleString()}`;
    kpiAlerts.textContent = data.open_alerts_count;
    alertCountPill.textContent = data.open_alerts_count;
  } catch (err) {
    console.error("Analytics fetch error:", err);
  }
}

async function loadTransactions() {
  try {
    const res = await fetch(`${API_BASE}/api/transactions`);
    if (!res.ok) return;
    const txs = await res.json();
    renderTransactionsTable(txs);
  } catch (err) {
    console.error(err);
  }
}

function renderTransactionsTable(txs) {
  if (txs.length === 0) {
    txTbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:1.5rem;">No transactions recorded.</td></tr>`;
    return;
  }

  txTbody.innerHTML = txs.map(t => `
    <tr>
      <td><strong>${escapeHtml(t.merchant_name)}</strong><br><span style="color:var(--text-dim);font-size:0.7rem;">${escapeHtml(t.merchant_category)}</span></td>
      <td><code>${escapeHtml(t.user_id)}</code><br><span style="color:var(--text-dim);font-size:0.7rem;">*${t.card_last4}</span></td>
      <td><strong>$${t.amount.toFixed(2)}</strong></td>
      <td><span style="font-family:var(--font-mono);">${t.risk_score}/100</span></td>
      <td><span class="badge-status ${t.decision}">${t.decision}</span></td>
    </tr>
  `).join("");
}

async function loadAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts?status=OPEN`);
    if (!res.ok) return;
    const alerts = await res.json();
    renderAlertsStream(alerts);
  } catch (err) {
    console.error(err);
  }
}

function renderAlertsStream(alerts) {
  if (alerts.length === 0) {
    alertsStream.innerHTML = `<div class="empty-state" style="padding:2rem;text-align:center;color:var(--accent-emerald);">All compliance alerts resolved. Network clean.</div>`;
    return;
  }

  alertsStream.innerHTML = alerts.map(a => `
    <div class="alert-item ${a.severity}">
      <div class="alert-top">
        <span class="alert-sev ${a.severity}">● ${a.severity} Threat Alert</span>
        <span style="color:var(--text-dim);">${a.created_at}</span>
      </div>
      <div class="alert-reason">${escapeHtml(a.alert_reason)}</div>
      <div class="alert-actions">
        <button class="btn-small" onclick="updateAlertStatus('${a.id}', 'RESOLVED')">✓ Resolve Incident</button>
        <button class="btn-small" style="color:var(--text-dim);" onclick="updateAlertStatus('${a.id}', 'DISMISSED')">Dismiss</button>
      </div>
    </div>
  `).join("");
}

async function handleEvalSubmit(e) {
  e.preventDefault();
  const submitBtn = document.getElementById("btn-eval");
  submitBtn.disabled = true;
  submitBtn.textContent = "Screening Anomaly Engine...";

  const payload = {
    user_id: userIdInput.value.trim(),
    card_last4: cardLast4Input.value.trim(),
    amount: parseFloat(amountInput.value),
    merchant_name: merchantNameInput.value.trim(),
    merchant_category: merchantCatInput.value,
    ip_address: "192.168.1.100",
    latitude: parseFloat(latInput.value),
    longitude: parseFloat(lonInput.value),
    device_id: deviceIdInput.value.trim()
  };

  try {
    const res = await fetch(`${API_BASE}/api/transactions/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Screening failed: ${err.detail || "Validation Error"}`);
      return;
    }

    const result = await res.json();
    displayEvalResult(result);
    await loadAnalytics();
    await loadTransactions();
    await loadAlerts();
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "⚡ Screen Transaction";
  }
}

function displayEvalResult(result) {
  evalResultBox.classList.remove("hidden");
  resDecisionBadge.className = `decision-badge ${result.decision}`;
  resDecisionBadge.textContent = result.decision;

  resScoreNum.textContent = result.risk_score;
  if (result.decision === "BLOCKED") {
    resScoreNum.style.color = "var(--accent-crimson)";
  } else if (result.decision === "REVIEW") {
    resScoreNum.style.color = "var(--accent-amber)";
  } else {
    resScoreNum.style.color = "var(--accent-emerald)";
  }

  if (result.risk_factors.length === 0) {
    resFactorsList.innerHTML = `<div class="no-factors">Zero anomalies detected. Clean baseline transaction.</div>`;
  } else {
    resFactorsList.innerHTML = result.risk_factors.map(f => `
      <div class="factor-pill">
        <div class="factor-head">
          <span>${escapeHtml(f.factor_code)}</span>
          <span>+${f.impact} Risk Pts</span>
        </div>
        <div style="color:var(--text-muted);">${escapeHtml(f.description)}</div>
      </div>
    `).join("");
  }
}

async function updateAlertStatus(alertId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/api/alerts/${alertId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      await loadAlerts();
      await loadAnalytics();
    }
  } catch (err) {
    console.error("Alert status update failed:", err);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
