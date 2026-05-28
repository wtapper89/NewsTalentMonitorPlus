const configSourceEl = document.getElementById('configSource')
const configPathEl = document.getElementById('configPath')
const configCountEl = document.getElementById('configCount')
const globalConfigEl = document.getElementById('globalConfig')
const micConfigsEl = document.getElementById('micConfigs')
const configFormEl = document.getElementById('configForm')
const saveStatusEl = document.getElementById('saveStatus')

const DEFAULT_FIELDS = {
  shure_name: 'name',
  battery_percent: 'battery.percent',
  signal_strength: 'rf.signalPercent',
  audio_level: 'audio.level',
  is_online: 'status.online',
  errors: 'errors',
}

let configState = {
  source: 'mock',
  mapping_file: '',
  micboard: {},
  display: {},
  companion: {},
  auth: {},
  default_connection: {},
  mics: [],
}
let ndiSources = []
let ndiStatus = null

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function saveStatus(message, status = '') {
  saveStatusEl.textContent = message
  saveStatusEl.className = `save-status ${status}`.trim()
}

function buildGlobalFields() {
  const auth = configState.auth || {}
  const defaults = configState.default_connection || {}
  const display = configState.display || {}
  const companion = configState.companion || {}

  globalConfigEl.innerHTML = `
    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Display</h3>
          <p>Fullscreen Pi layout, show title, and preview source.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          <span class="field-label">Show title mode</span>
          <select data-global-field="display.show_title_mode">
            <option value="manual" ${String(display.show_title_mode || 'manual') === 'manual' ? 'selected' : ''}>manual</option>
            <option value="companion" ${String(display.show_title_mode || '') === 'companion' ? 'selected' : ''}>companion</option>
          </select>
        </label>
        <label class="stack">
          <span class="field-label">Manual show title</span>
          <input type="text" value="${escapeHtml(display.manual_show_title ?? 'TVC NEWS')}" data-global-field="display.manual_show_title" />
        </label>
        <label class="stack">
          <span class="field-label">Preview mode</span>
          <select data-global-field="display.preview_mode">
            <option value="placeholder" ${String(display.preview_mode || 'placeholder') === 'placeholder' ? 'selected' : ''}>placeholder</option>
            <option value="ndi" ${String(display.preview_mode || '') === 'ndi' ? 'selected' : ''}>ndi</option>
            <option value="iframe" ${String(display.preview_mode || '') === 'iframe' ? 'selected' : ''}>iframe</option>
            <option value="image" ${String(display.preview_mode || '') === 'image' ? 'selected' : ''}>image</option>
            <option value="video" ${String(display.preview_mode || '') === 'video' ? 'selected' : ''}>video</option>
          </select>
        </label>
        <label class="stack">
          <span class="field-label">Preview URL</span>
          <input type="text" value="${escapeHtml(display.preview_url ?? '')}" data-global-field="display.preview_url" placeholder="http://127.0.0.1:8080/preview" />
        </label>
        <label class="stack">
          <span class="field-label">NDI source name</span>
          <div class="input-row">
            <input type="text" value="${escapeHtml(display.preview_source_name ?? '')}" data-global-field="display.preview_source_name" placeholder="StudioCam 1" list="ndiSources" />
            <button type="button" class="secondary button-inline" id="scanNdiButton">Scan</button>
          </div>
          <datalist id="ndiSources"></datalist>
        </label>
        <label class="stack">
          <span class="field-label">Preview poster URL</span>
          <input type="text" value="${escapeHtml(display.preview_poster_url ?? '')}" data-global-field="display.preview_poster_url" placeholder="http://127.0.0.1:8080/poster.jpg" />
        </label>
        <label class="stack">
          <span class="field-label">Font family</span>
          <input type="text" value="${escapeHtml(display.font_family ?? 'Gotham, Montserrat, Arial, sans-serif')}" data-global-field="display.font_family" />
        </label>
      </div>
      <div class="ndi-panel">
        <div class="ndi-panel-head">
          <div>
            <strong>NDI sources</strong>
            <span>${ndiSources.length ? `${ndiSources.length} found` : 'Scan to list sources'}</span>
          </div>
          <button type="button" class="secondary button-inline" id="refreshNdiStatusButton">Status</button>
        </div>
        <div class="ndi-source-list">
          ${
            ndiSources.length
              ? ndiSources
                  .map((source) => {
                    const isSelected = source.name === String(display.preview_source_name || '').trim()
                    return `
                      <button type="button" class="ndi-source-button ${isSelected ? 'is-selected' : ''}" data-ndi-source="${escapeHtml(source.name)}">
                        <span>${escapeHtml(source.name)}</span>
                        <small>${escapeHtml(source.url || 'NDI source')}</small>
                      </button>
                    `
                  })
                  .join('')
              : '<div class="ndi-empty">No scan results yet.</div>'
          }
        </div>
        <div class="ndi-status">
          ${renderNdiStatus(display)}
        </div>
      </div>
    </article>

    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Companion title source</h3>
          <p>Read a module variable from Companion, such as a Cuez show title.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          <span class="field-label">Enable Companion polling</span>
          <select data-global-field="companion.enabled">
            <option value="true" ${companion.enabled ? 'selected' : ''}>true</option>
            <option value="false" ${!companion.enabled ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          <span class="field-label">Companion base URL</span>
          <input type="text" value="${escapeHtml(companion.base_url ?? 'http://127.0.0.1:8000')}" data-global-field="companion.base_url" />
        </label>
        <label class="stack">
          <span class="field-label">Connection label</span>
          <input type="text" value="${escapeHtml(companion.connection_label ?? 'Cuez')}" data-global-field="companion.connection_label" />
        </label>
        <label class="stack">
          <span class="field-label">Variable name</span>
          <input type="text" value="${escapeHtml(companion.variable_name ?? '')}" data-global-field="companion.variable_name" placeholder="segment_title" />
        </label>
      </div>
    </article>

    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Receiver defaults</h3>
          <p>QLX-D default connection settings and optional auth for System API mode.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          <span class="field-label">Auth type</span>
          <select data-global-field="auth.type">
            <option value="none" ${String(auth.type || 'none') === 'none' ? 'selected' : ''}>none</option>
            <option value="bearer" ${String(auth.type || '') === 'bearer' ? 'selected' : ''}>bearer</option>
          </select>
        </label>
        <label class="stack">
          <span class="field-label">Default scheme</span>
          <select data-global-field="default_connection.scheme">
            <option value="tcp" ${defaults.scheme === 'tcp' ? 'selected' : ''}>tcp</option>
            <option value="http" ${defaults.scheme === 'http' ? 'selected' : ''}>http</option>
            <option value="https" ${defaults.scheme === 'https' ? 'selected' : ''}>https</option>
          </select>
        </label>
        <label class="stack">
          <span class="field-label">Default port</span>
          <input type="number" min="1" max="65535" value="${escapeHtml(defaults.port ?? 2202)}" data-global-field="default_connection.port" />
        </label>
        <label class="stack">
          <span class="field-label">Token URL</span>
          <input type="text" value="${escapeHtml(auth.token_url ?? '')}" data-global-field="auth.token_url" />
        </label>
        <label class="stack">
          <span class="field-label">Client ID</span>
          <input type="text" value="${escapeHtml(auth.client_id ?? '')}" data-global-field="auth.client_id" />
        </label>
        <label class="stack">
          <span class="field-label">Client secret</span>
          <input type="password" value="${escapeHtml(auth.client_secret ?? '')}" data-global-field="auth.client_secret" />
        </label>
        <label class="stack">
          <span class="field-label">Grant type</span>
          <input type="text" value="${escapeHtml(auth.grant_type ?? 'client_credentials')}" data-global-field="auth.grant_type" />
        </label>
      </div>
    </article>
  `
}

function renderNdiStatus(display) {
  if (!ndiStatus) {
    return 'NDI status has not been checked yet.'
  }
  const source = ndiStatus.source_name || display.preview_source_name || 'none'
  const frame = ndiStatus.has_frame
    ? `${ndiStatus.frame_width}x${ndiStatus.frame_height}, ${ndiStatus.seconds_since_frame}s ago`
    : 'no frame yet'
  const error = ndiStatus.last_error ? ` Error: ${escapeHtml(ndiStatus.last_error)}` : ''
  return `Status: ${escapeHtml(ndiStatus.connection_status || 'unknown')} | Source: ${escapeHtml(source)} | Frame: ${escapeHtml(frame)}${error}`
}

function buildMicCards() {
  if (!configState.mics.length) {
    micConfigsEl.innerHTML = '<div class="empty">No mic connection entries yet.</div>'
    return
  }

  micConfigsEl.innerHTML = configState.mics
    .map(
      (mic, index) => `
        <article class="config-card">
          <div class="config-card-head">
            <div>
              <h3>${escapeHtml(mic.default_name || mic.id)}</h3>
              <p>${escapeHtml(mic.id)}</p>
            </div>
            <button type="button" class="secondary button-inline" data-remove-mic="${index}">Remove</button>
          </div>

          <div class="config-card-grid">
            <label class="stack">
              <span class="field-label">Mic ID</span>
              <input type="text" value="${escapeHtml(mic.id)}" data-mic-index="${index}" data-mic-field="id" />
            </label>
            <label class="stack">
              <span class="field-label">Display label</span>
              <input type="text" value="${escapeHtml(mic.default_name)}" data-mic-index="${index}" data-mic-field="default_name" />
            </label>
            <label class="stack">
              <span class="field-label">Assigned to</span>
              <input type="text" value="${escapeHtml(mic.assigned_to ?? '')}" data-mic-index="${index}" data-mic-field="assigned_to" placeholder="Lead Pastor" />
            </label>
            <label class="stack">
              <span class="field-label">Receiver label</span>
              <input type="text" value="${escapeHtml(mic.receiver_name ?? '')}" data-mic-index="${index}" data-mic-field="receiver_name" />
            </label>
            <label class="stack">
              <span class="field-label">Channel</span>
              <input type="text" value="${escapeHtml(mic.channel_label ?? '')}" data-mic-index="${index}" data-mic-field="channel_label" />
            </label>
            <label class="stack">
              <span class="field-label">Receiver channel</span>
              <input type="number" min="1" max="4" value="${escapeHtml(mic.receiver_channel ?? 1)}" data-mic-index="${index}" data-mic-field="receiver_channel" />
            </label>
            <label class="stack">
              <span class="field-label">Device IP / host</span>
              <input type="text" value="${escapeHtml(mic.device_ip ?? '')}" data-mic-index="${index}" data-mic-field="device_ip" placeholder="192.168.1.40" />
            </label>
            <label class="stack">
              <span class="field-label">Scheme</span>
              <select data-mic-index="${index}" data-mic-field="scheme">
                <option value="tcp" ${mic.scheme === 'tcp' ? 'selected' : ''}>tcp</option>
                <option value="http" ${mic.scheme === 'http' ? 'selected' : ''}>http</option>
                <option value="https" ${mic.scheme === 'https' ? 'selected' : ''}>https</option>
              </select>
            </label>
            <label class="stack">
              <span class="field-label">Port</span>
              <input type="number" min="1" max="65535" value="${escapeHtml(mic.port ?? configState.default_connection.port ?? 443)}" data-mic-index="${index}" data-mic-field="port" />
            </label>
            <label class="stack">
              <span class="field-label">Telemetry path</span>
              <input type="text" value="${escapeHtml(mic.telemetry_path ?? '')}" data-mic-index="${index}" data-mic-field="telemetry_path" placeholder="/api/receivers/rack-a/channels/a1" />
            </label>
            <label class="stack">
              <span class="field-label">Rename path</span>
              <input type="text" value="${escapeHtml(mic.rename_path ?? '')}" data-mic-index="${index}" data-mic-field="rename_path" placeholder="/api/receivers/rack-a/channels/a1/name" />
            </label>
          </div>
        </article>
      `,
    )
    .join('')
}

function render() {
  configSourceEl.textContent = configState.source
  configPathEl.textContent = configState.mapping_file
  configCountEl.textContent = String(configState.mics.length)
  buildGlobalFields()
  buildMicCards()
}

function nextMicId() {
  const used = new Set(configState.mics.map((mic) => mic.id))
  let index = configState.mics.length + 1
  while (used.has(`mic-${index}`)) {
    index += 1
  }
  return `mic-${index}`
}

function newMicConfig() {
  const id = nextMicId()
  return {
    id,
    default_name: `MIC ${configState.mics.length + 1}`,
    receiver_name: '',
    channel_label: '',
    micboard_slot: 0,
    receiver_channel: 1,
    device_ip: '',
    scheme: configState.default_connection.scheme || 'tcp',
    port: Number(configState.default_connection.port || 2202),
    telemetry_path: '',
    telemetry_method: 'GET',
    rename_path: '',
    rename_method: 'PUT',
    fields: { ...DEFAULT_FIELDS },
    rename_body: { name: '{name}' },
  }
}

function setDeepValue(target, dottedField, value) {
  const [root, key] = dottedField.split('.')
  target[root] = target[root] || {}
  target[root][key] = value
}

function normalizeForSave() {
  const authType = String(configState.auth.type || 'none').trim() || 'none'
  return {
    display: {
      show_title_mode: String(configState.display.show_title_mode || 'manual').trim() || 'manual',
      manual_show_title: String(configState.display.manual_show_title || 'TVC NEWS').trim() || 'TVC NEWS',
      preview_mode: String(configState.display.preview_mode || 'placeholder').trim() || 'placeholder',
      preview_url: String(configState.display.preview_url || '').trim(),
      preview_source_name: String(configState.display.preview_source_name || '').trim(),
      preview_poster_url: String(configState.display.preview_poster_url || '').trim(),
      font_family: String(configState.display.font_family || 'Gotham, Montserrat, Arial, sans-serif').trim(),
    },
    companion: {
      enabled: Boolean(configState.companion.enabled),
      base_url: String(configState.companion.base_url || 'http://127.0.0.1:8000').trim(),
      connection_label: String(configState.companion.connection_label || 'Cuez').trim(),
      variable_name: String(configState.companion.variable_name || '').trim(),
    },
    auth: {
      type: authType,
      token_url: String(configState.auth.token_url || '').trim(),
      grant_type: String(configState.auth.grant_type || 'client_credentials').trim() || 'client_credentials',
      client_id: String(configState.auth.client_id || '').trim(),
      client_secret: String(configState.auth.client_secret || '').trim(),
      scope: '',
      username: '',
      password: '',
    },
    default_connection: {
      scheme: String(configState.default_connection.scheme || 'tcp').trim() || 'tcp',
      port: Number(configState.default_connection.port || 2202),
    },
    mics: configState.mics.map((mic) => ({
      id: String(mic.id || '').trim(),
      default_name: String(mic.default_name || '').trim(),
      receiver_name: String(mic.receiver_name || '').trim(),
      channel_label: String(mic.channel_label || '').trim(),
      micboard_slot: Number(mic.micboard_slot || 0),
      receiver_channel: Number(mic.receiver_channel || 1),
      device_ip: String(mic.device_ip || '').trim(),
      scheme: String(mic.scheme || configState.default_connection.scheme || 'tcp').trim() || 'tcp',
      port: Number(mic.port || configState.default_connection.port || 2202),
      telemetry_path: String(mic.telemetry_path || '').trim(),
      telemetry_method: 'GET',
      rename_path: String(mic.rename_path || '').trim(),
      rename_method: 'PUT',
      fields: mic.fields || { ...DEFAULT_FIELDS },
      rename_body: mic.rename_body || { name: '{name}' },
    })),
  }
}

async function fetchConfig() {
  const response = await fetch('/api/config')
  if (!response.ok) {
    throw new Error('Failed to load config')
  }
  configState = await response.json()
  render()
}

async function saveConfig() {
  const payload = normalizeForSave()
  const assignmentDrafts = configState.mics.map((mic) => ({
    id: String(mic.id || '').trim(),
    assigned_to: String(mic.assigned_to || '').trim(),
  }))
  const response = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Save failed' }))
    throw new Error(error.detail || 'Save failed')
  }

  const result = await response.json()
  configState = result.config
  ndiStatus = result.ndi_status || ndiStatus
  await saveAssignments(assignmentDrafts)
  applyAssignmentDrafts(assignmentDrafts)
  await refreshNdiStatus()
  render()
}

function applyAssignmentDrafts(assignments) {
  const byId = new Map(assignments.map((assignment) => [assignment.id, assignment.assigned_to]))
  configState.mics = configState.mics.map((mic) => ({
    ...mic,
    assigned_to: byId.get(String(mic.id || '').trim()) ?? mic.assigned_to ?? '',
  }))
}

async function saveAssignments(assignments) {
  for (const assignment of assignments) {
    if (!assignment.id) continue
    const response = await fetch(`/api/mics/${encodeURIComponent(assignment.id)}/assignment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assigned_to: assignment.assigned_to }),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `Failed to save assignment for ${assignment.id}` }))
      throw new Error(error.detail || `Failed to save assignment for ${assignment.id}`)
    }
  }
}

document.addEventListener('input', (event) => {
  const target = event.target
  if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return

  if (target.dataset.globalField) {
    let value
    if (target.type === 'number') {
      value = Number(target.value || 0)
    } else if (target instanceof HTMLSelectElement && target.value === 'true') {
      value = true
    } else if (target instanceof HTMLSelectElement && target.value === 'false') {
      value = false
    } else {
      value = target.value
    }
    setDeepValue(configState, target.dataset.globalField, value)
    return
  }

  const micIndex = target.dataset.micIndex
  const micField = target.dataset.micField
  if (micIndex === undefined || !micField) return
  const index = Number(micIndex)
  if (!configState.mics[index]) return
  configState.mics[index][micField] = target.type === 'number' ? Number(target.value || 0) : target.value
})

document.addEventListener('click', (event) => {
  const target = event.target
  if (!(target instanceof HTMLElement)) return

  if (target.id === 'addMicButton') {
    configState.mics.push(newMicConfig())
    render()
    saveStatus('Added new mic entry. Save to persist.')
    return
  }

  if (target.id === 'scanNdiButton') {
    scanNdiSources().catch((error) => {
      saveStatus(error.message, 'error')
    })
    return
  }

  if (target.id === 'refreshNdiStatusButton') {
    refreshNdiStatus()
      .then(() => {
        render()
        saveStatus('NDI status refreshed.', 'ok')
      })
      .catch((error) => saveStatus(error.message, 'error'))
    return
  }

  const ndiSourceButton = target.closest('[data-ndi-source]')
  if (ndiSourceButton instanceof HTMLElement) {
    configState.display = configState.display || {}
    configState.display.preview_mode = 'ndi'
    configState.display.preview_source_name = ndiSourceButton.dataset.ndiSource || ''
    render()
    saveStatus('NDI source selected. Save configuration to apply it.')
    return
  }

  if (target.dataset.removeMic) {
    const index = Number(target.dataset.removeMic)
    configState.mics.splice(index, 1)
    render()
    saveStatus('Removed mic entry. Save to persist.')
  }
})

async function scanNdiSources() {
  saveStatus('Scanning for NDI sources...')
  const response = await fetch('/api/ndi/sources')
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'NDI scan failed' }))
    throw new Error(error.detail || 'NDI scan failed')
  }
  const payload = await response.json()
  ndiSources = payload.sources || []
  const datalist = document.getElementById('ndiSources')
  if (datalist) {
    datalist.innerHTML = ndiSources
      .map((source) => `<option value="${escapeHtml(source.name)}"></option>`)
      .join('')
  }
  render()
  saveStatus(`${ndiSources.length} NDI source(s) found.`, 'ok')
}

async function refreshNdiStatus() {
  const response = await fetch('/api/ndi/status')
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'NDI status failed' }))
    throw new Error(error.detail || 'NDI status failed')
  }
  ndiStatus = await response.json()
}

configFormEl.addEventListener('submit', async (event) => {
  event.preventDefault()
  try {
    await saveConfig()
    saveStatus('Configuration saved.', 'ok')
  } catch (error) {
    saveStatus(error.message, 'error')
  }
})

fetchConfig().catch((error) => {
  saveStatus(error.message, 'error')
})
