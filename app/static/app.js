const boardEl = document.getElementById('board')
const summaryEl = document.getElementById('summaryCards')
const alertsEl = document.getElementById('alerts')
const sourceLabelEl = document.getElementById('sourceLabel')
const connectionLabelEl = document.getElementById('connectionLabel')
const updatedLabelEl = document.getElementById('updatedLabel')

const TREND_WIDTH = 260
const TREND_HEIGHT = 88
const drafts = new Map()
let refreshHandle = null

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function formatTimestamp(value) {
  if (!value) return '...'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })
}

function connectionLabel(status) {
  if (status === 'ok') return 'Live'
  if (status === 'warning') return 'Cached'
  if (status === 'error') return 'Fault'
  return 'Starting'
}

function meterClass(mic, key) {
  if (!mic.is_online) return 'offline'
  if (key === 'battery_percent' && mic.battery_percent <= 25) return 'warning'
  if (key === 'signal_strength' && mic.signal_strength <= 30) return 'warning'
  return ''
}

function clampPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 0
  return Math.max(0, Math.min(100, numeric))
}

function historyWindowSeconds(mic, fallback = 60) {
  const numeric = Number(mic.history?.window_seconds)
  if (!Number.isFinite(numeric) || numeric <= 0) return fallback
  return numeric
}

function historySeries(mic, key) {
  return Array.isArray(mic.history?.[key]) ? mic.history[key] : []
}

function buildTrendGridPath(width, height) {
  const horizontal = [0.2, 0.5, 0.8].map((ratio) => `M 0 ${(height * ratio).toFixed(2)} H ${width}`)
  const vertical = [0.25, 0.5, 0.75].map((ratio) => `M ${(width * ratio).toFixed(2)} 0 V ${height}`)
  return [...horizontal, ...vertical].join(' ')
}

function buildTrendGeometry(series, windowSeconds, width, height) {
  const cleaned = series
    .map((sample) => ({
      timestampMs: Number(sample?.timestamp_ms) || 0,
      value: clampPercent(sample?.value),
    }))
    .filter((sample) => sample.timestampMs > 0)
    .sort((left, right) => left.timestampMs - right.timestampMs)

  if (!cleaned.length) {
    const baseline = (height - 4).toFixed(2)
    return {
      hasData: false,
      line: `0,${baseline} ${width},${baseline}`,
      area: `M 0 ${height} L 0 ${baseline} L ${width} ${baseline} L ${width} ${height} Z`,
    }
  }

  const latestTimestamp = cleaned[cleaned.length - 1].timestampMs
  const startTimestamp = latestTimestamp - windowSeconds * 1000
  const points = cleaned.map((sample) => {
    const x = Math.max(0, Math.min(width, ((sample.timestampMs - startTimestamp) / (windowSeconds * 1000)) * width))
    const y = Math.max(2, Math.min(height - 2, height - (sample.value / 100) * height))
    return { x, y }
  })

  if (points.length === 1) {
    const only = points[0]
    const left = Math.max(0, only.x - 1)
    const right = Math.min(width, only.x + 1)
    points.unshift({ x: left, y: only.y })
    points.push({ x: right, y: only.y })
  }

  const line = points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ')
  const area = [
    `M ${points[0].x.toFixed(2)} ${height}`,
    ...points.map((point) => `L ${point.x.toFixed(2)} ${point.y.toFixed(2)}`),
    `L ${points[points.length - 1].x.toFixed(2)} ${height}`,
    'Z',
  ].join(' ')

  return { hasData: true, line, area }
}

function renderTrendChart(label, value, series, tone, windowSeconds) {
  const geometry = buildTrendGeometry(series, windowSeconds, TREND_WIDTH, TREND_HEIGHT)
  const gridPath = buildTrendGridPath(TREND_WIDTH, TREND_HEIGHT)
  return `
    <section class="trend-panel ${tone}">
      <div class="trend-head">
        <div>
          <span class="field-label">${escapeHtml(label)}</span>
          <span class="trend-window">${escapeHtml(`${windowSeconds}s window`)}</span>
        </div>
        <strong class="trend-value">${escapeHtml(`${Math.round(clampPercent(value))}%`)}</strong>
      </div>
      <svg class="trend-svg ${tone}" viewBox="0 0 ${TREND_WIDTH} ${TREND_HEIGHT}" preserveAspectRatio="none" aria-hidden="true">
        <path class="trend-grid" d="${gridPath}"></path>
        <path class="trend-area ${tone} ${geometry.hasData ? '' : 'is-empty'}" d="${geometry.area}"></path>
        <polyline class="trend-line ${tone} ${geometry.hasData ? '' : 'is-empty'}" points="${geometry.line}"></polyline>
      </svg>
    </section>
  `
}

function draftKey(micId, field) {
  return `${micId}:${field}`
}

function readDraft(micId, field, fallback) {
  return drafts.get(draftKey(micId, field)) ?? fallback
}

function renderSummary(state) {
  const cards = [
    ['Live mics', state.summary.total],
    ['Assigned', state.summary.assigned],
    ['Low battery', state.summary.low_battery],
    ['Offline', state.summary.offline],
    ['Errors', state.summary.with_errors],
  ]
  summaryEl.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="summary-card">
          <span class="status-label">${escapeHtml(label)}</span>
          <strong class="summary-value">${escapeHtml(value)}</strong>
        </article>
      `,
    )
    .join('')
}

function renderAlerts(state) {
  if (!state.alerts.length) {
    alertsEl.innerHTML = '<div class="empty">No active alerts.</div>'
    return
  }

  alertsEl.innerHTML = state.alerts
    .map(
      (alert) => `
        <article class="alert-card">
          <h3>${escapeHtml(alert.title)}</h3>
          <p>${escapeHtml(alert.detail)}</p>
        </article>
      `,
    )
    .join('')
}

function renderBoard(state) {
  if (!state.mics.length) {
    boardEl.innerHTML = `<div class="empty">${escapeHtml(state.connection_message || 'No microphones found yet.')}</div>`
    return
  }

  boardEl.innerHTML = state.mics
    .map((mic) => {
      const renameDraft = readDraft(mic.id, 'name', mic.display_name)
      const assigneeDraft = readDraft(mic.id, 'assignee', mic.assigned_to)
      const windowSeconds = historyWindowSeconds(mic, state.telemetry_window_seconds || 60)

      return `
        <article class="mic-card ${escapeHtml(mic.health)}">
          <div class="mic-topline">
            <span class="channel-chip">${escapeHtml(mic.channel_label || mic.id)}</span>
            <span class="status-chip ${escapeHtml(mic.health)}">${escapeHtml(mic.health)}</span>
          </div>

          <h3 class="mic-name">${escapeHtml(mic.display_name)}</h3>
          <p class="mic-receiver">${escapeHtml(mic.receiver_name || 'Receiver not labeled')}</p>

          <div class="mic-meta">
            <div class="metric">
              <span class="metric-label">Battery</span>
              <strong class="metric-value">${escapeHtml(mic.battery_percent)}%</strong>
            </div>
            <div class="metric">
              <span class="metric-label">RF</span>
              <strong class="metric-value">${escapeHtml(mic.signal_strength)}%</strong>
            </div>
            <div class="metric">
              <span class="metric-label">Audio</span>
              <strong class="metric-value">${escapeHtml(mic.audio_level)}%</strong>
            </div>
          </div>

          <div class="meter-row meter-row-compact">
            <div class="meter">
              <span class="field-label">Battery</span>
              <div class="meter-bar"><div class="meter-fill ${meterClass(mic, 'battery_percent')}" style="--value:${escapeHtml(mic.battery_percent)}%"></div></div>
            </div>
          </div>

          <div class="trend-stack">
            ${renderTrendChart('Audio level', mic.audio_level, historySeries(mic, 'audio_level'), 'audio', windowSeconds)}
            ${renderTrendChart('RF strength', mic.signal_strength, historySeries(mic, 'signal_strength'), 'signal', windowSeconds)}
          </div>

          <form data-rename-form="${escapeHtml(mic.id)}" class="stack">
            <label class="stack">
              <span class="field-label">Shure mic name</span>
              <div class="input-row">
                <input
                  type="text"
                  name="name"
                  value="${escapeHtml(renameDraft)}"
                  data-draft-mic="${escapeHtml(mic.id)}"
                  data-draft-field="name"
                  autocomplete="off"
                />
                <button type="submit">Rename</button>
              </div>
            </label>
          </form>

          <form data-assignment-form="${escapeHtml(mic.id)}" class="stack">
            <label class="stack">
              <span class="field-label">Assigned to</span>
              <div class="input-row">
                <input
                  type="text"
                  name="assigned_to"
                  value="${escapeHtml(assigneeDraft)}"
                  data-draft-mic="${escapeHtml(mic.id)}"
                  data-draft-field="assignee"
                  autocomplete="off"
                />
                <button type="submit" class="secondary">Save</button>
              </div>
            </label>
          </form>

          <div class="error-wrap">
            ${
              mic.errors.length
                ? mic.errors.map((error) => `<span class="error-tag">${escapeHtml(error)}</span>`).join('')
                : '<span class="field-label">No active errors</span>'
            }
          </div>
        </article>
      `
    })
    .join('')
}

function render(state) {
  sourceLabelEl.textContent = state.source
  connectionLabelEl.textContent = connectionLabel(state.connection_status)
  updatedLabelEl.textContent = formatTimestamp(state.last_refresh)
  renderSummary(state)
  renderBoard(state)
  renderAlerts(state)
}

async function fetchState() {
  const response = await fetch('/api/state')
  if (!response.ok) {
    throw new Error('Failed to load state')
  }
  const state = await response.json()
  render(state)
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

document.addEventListener('input', (event) => {
  const input = event.target
  if (!(input instanceof HTMLInputElement)) return
  const micId = input.dataset.draftMic
  const field = input.dataset.draftField
  if (!micId || !field) return
  drafts.set(draftKey(micId, field), input.value)
})

document.addEventListener('submit', async (event) => {
  const form = event.target
  if (!(form instanceof HTMLFormElement)) return
  event.preventDefault()

  try {
    if (form.dataset.renameForm) {
      const micId = form.dataset.renameForm
      const name = new FormData(form).get('name')
      const state = await postJson(`/api/mics/${encodeURIComponent(micId)}/rename`, { name })
      drafts.delete(draftKey(micId, 'name'))
      render(state)
      return
    }

    if (form.dataset.assignmentForm) {
      const micId = form.dataset.assignmentForm
      const assigned_to = new FormData(form).get('assigned_to')
      const state = await postJson(`/api/mics/${encodeURIComponent(micId)}/assignment`, { assigned_to })
      drafts.delete(draftKey(micId, 'assignee'))
      render(state)
    }
  } catch (error) {
    window.alert(error.message)
  }
})

async function start() {
  try {
    await fetchState()
  } catch (error) {
    boardEl.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`
  }

  refreshHandle = window.setInterval(() => {
    fetchState().catch((error) => {
      boardEl.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`
    })
  }, 2000)
}

window.addEventListener('beforeunload', () => {
  if (refreshHandle) {
    window.clearInterval(refreshHandle)
  }
})

start()
