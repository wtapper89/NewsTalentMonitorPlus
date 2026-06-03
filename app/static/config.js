const configSourceEl = document.getElementById('configSource')
const configPathEl = document.getElementById('configPath')
const configCountEl = document.getElementById('configCount')
const globalConfigEl = document.getElementById('globalConfig')
const micConfigsEl = document.getElementById('micConfigs')
const micConfigSectionEl = document.getElementById('micConfigSection')
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
  anchor_photos: {},
  room_sign: {},
  auth: {},
  default_connection: {},
  mics: [],
}
let ndiSources = []
let ndiStatus = null
let activeConfigTab = 'display'

const CONFIG_TABS = [
  ['display', 'Display'],
  ['room-sign', 'Room Sign'],
  ['companion', 'Companion'],
  ['photos', 'Photos'],
  ['receivers', 'Receivers'],
  ['mics', 'Mics'],
]

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function normalizeHexColor(value, fallback) {
  const candidate = String(value || '').trim()
  return /^#[0-9a-fA-F]{6}$/.test(candidate) ? candidate : fallback
}

function saveStatus(message, status = '') {
  saveStatusEl.textContent = message
  saveStatusEl.className = `save-status ${status}`.trim()
}

function fieldLabel(label, help) {
  const helpButton = help
    ? `<button type="button" class="help-button" title="${escapeHtml(help)}" aria-label="${escapeHtml(`${label}: ${help}`)}">?</button>`
    : ''
  return `<span class="field-label"><span>${escapeHtml(label)}</span>${helpButton}</span>`
}

function renderTabs() {
  return `
    <div class="config-tabs" role="tablist" aria-label="Configuration sections">
      ${CONFIG_TABS.map(
        ([id, label]) => `
          <button type="button" class="config-tab ${activeConfigTab === id ? 'is-active' : ''}" data-config-tab="${id}" role="tab" aria-selected="${activeConfigTab === id ? 'true' : 'false'}">
            ${escapeHtml(label)}
          </button>
        `,
      ).join('')}
    </div>
  `
}

function tabPanel(id, content) {
  return `<section class="config-tab-panel ${activeConfigTab === id ? 'is-active' : ''}" data-config-tab-panel="${id}">${content}</section>`
}

function buildGlobalFields() {
  const auth = configState.auth || {}
  const defaults = configState.default_connection || {}
  const display = configState.display || {}
  const companion = configState.companion || {}
  const anchorPhotos = configState.anchor_photos || {}
  const roomSign = configState.room_sign || {}

  globalConfigEl.innerHTML = `
    ${renderTabs()}
    ${tabPanel('display', `
    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Display</h3>
          <p>Fullscreen Pi layout and the large video preview.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          ${fieldLabel('Show title mode', 'Legacy option for the old title area. The kiosk now uses Now and Next instead.')}
          <select data-global-field="display.show_title_mode">
            <option value="manual" ${String(display.show_title_mode || 'manual') === 'manual' ? 'selected' : ''}>manual</option>
            <option value="companion" ${String(display.show_title_mode || '') === 'companion' ? 'selected' : ''}>companion</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Manual show title', 'Fallback title kept for compatibility with older display layouts.')}
          <input type="text" value="${escapeHtml(display.manual_show_title ?? 'TVC NEWS')}" data-global-field="display.manual_show_title" />
        </label>
        <label class="stack">
          ${fieldLabel('Preview mode', 'Use NDI for the built-in NDI receiver. Use iframe/image/video only for browser-playable URLs.')}
          <select data-global-field="display.preview_mode">
            <option value="placeholder" ${String(display.preview_mode || 'placeholder') === 'placeholder' ? 'selected' : ''}>placeholder</option>
            <option value="ndi" ${String(display.preview_mode || '') === 'ndi' ? 'selected' : ''}>ndi</option>
            <option value="iframe" ${String(display.preview_mode || '') === 'iframe' ? 'selected' : ''}>iframe</option>
            <option value="image" ${String(display.preview_mode || '') === 'image' ? 'selected' : ''}>image</option>
            <option value="video" ${String(display.preview_mode || '') === 'video' ? 'selected' : ''}>video</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Preview URL', 'Only needed when Preview mode is iframe, image, or video. NDI mode ignores this field.')}
          <input type="text" value="${escapeHtml(display.preview_url ?? '')}" data-global-field="display.preview_url" placeholder="http://127.0.0.1:8080/preview" />
        </label>
        <label class="stack">
          ${fieldLabel('NDI source name', 'The exact NDI source to show in the large preview. Use Scan to find sources visible to the Pi.')}
          <div class="input-row">
            <input type="text" value="${escapeHtml(display.preview_source_name ?? '')}" data-global-field="display.preview_source_name" placeholder="StudioCam 1" list="ndiSources" />
            <button type="button" class="secondary button-inline" id="scanNdiButton">Scan</button>
          </div>
          <datalist id="ndiSources"></datalist>
        </label>
        <label class="stack">
          ${fieldLabel('Preview poster URL', 'Optional poster image for video URL mode. Not used for NDI.')}
          <input type="text" value="${escapeHtml(display.preview_poster_url ?? '')}" data-global-field="display.preview_poster_url" placeholder="http://127.0.0.1:8080/poster.jpg" />
        </label>
        <label class="stack">
          ${fieldLabel('Font family', 'Fonts Chromium should try for the kiosk display. The font must be installed on the Pi.')}
          <input type="text" value="${escapeHtml(display.font_family ?? 'Gotham, Montserrat, Arial, sans-serif')}" data-global-field="display.font_family" />
        </label>
        <label class="stack">
          ${fieldLabel('Show Now box', 'Hide this if you do not want the green PGM/Now panel in the top bar.')}
          <select data-global-field="display.now_panel_enabled">
            <option value="true" ${display.now_panel_enabled !== false ? 'selected' : ''}>true</option>
            <option value="false" ${display.now_panel_enabled === false ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Now label', 'The label shown at the left side of the PGM/Now box.')}
          <input type="text" value="${escapeHtml(display.now_panel_label ?? 'Now')}" data-global-field="display.now_panel_label" />
        </label>
        <label class="stack">
          ${fieldLabel('Now border color', 'Border and label color for the PGM/Now box.')}
          <input type="color" value="${escapeHtml(normalizeHexColor(display.now_panel_border_color, '#1cff00'))}" data-global-field="display.now_panel_border_color" />
        </label>
        <label class="stack">
          ${fieldLabel('Show Next box', 'Hide this if you do not want the yellow PVW/Next panel in the top bar.')}
          <select data-global-field="display.next_panel_enabled">
            <option value="true" ${display.next_panel_enabled !== false ? 'selected' : ''}>true</option>
            <option value="false" ${display.next_panel_enabled === false ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Next label', 'The label shown at the left side of the PVW/Next box.')}
          <input type="text" value="${escapeHtml(display.next_panel_label ?? 'Next')}" data-global-field="display.next_panel_label" />
        </label>
        <label class="stack">
          ${fieldLabel('Next border color', 'Border and label color for the PVW/Next box.')}
          <input type="color" value="${escapeHtml(normalizeHexColor(display.next_panel_border_color, '#fff200'))}" data-global-field="display.next_panel_border_color" />
        </label>
        <label class="stack">
          ${fieldLabel('Show status sign', 'Shows a neon ON AIR, RECORDING, or custom text sign in the blank space to the right of the preview video.')}
          <select data-global-field="display.status_sign_enabled">
            <option value="true" ${display.status_sign_enabled !== false ? 'selected' : ''}>true</option>
            <option value="false" ${display.status_sign_enabled === false ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Fallback status text', 'Used when the status sign variable is blank. Any custom value becomes neon text.')}
          <input type="text" value="${escapeHtml(display.status_sign_custom_text ?? '')}" data-global-field="display.status_sign_custom_text" placeholder="STANDBY" />
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
    `)}

    ${tabPanel('room-sign', `
    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Room sign</h3>
          <p>Separate 1920x720 on-air sign and 25Live schedule view.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          ${fieldLabel('Enable room sign', 'Turn this on to allow the room sign page to fetch and display 25Live room events.')}
          <select data-global-field="room_sign.enabled">
            <option value="true" ${roomSign.enabled ? 'selected' : ''}>true</option>
            <option value="false" ${!roomSign.enabled ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Fallback room name', 'Shown when the room is not on air and there are no upcoming events to list.')}
          <input type="text" value="${escapeHtml(roomSign.room_name ?? 'Studio')}" data-global-field="room_sign.room_name" placeholder="COM 251 - John Williams Studio" />
        </label>
        <label class="stack">
          ${fieldLabel('25Live room ID', 'The 25Live space_id for this room. For your John Williams Studio example, use 1536.')}
          <input type="text" value="${escapeHtml(roomSign.room_id ?? '')}" data-global-field="room_sign.room_id" placeholder="1536" />
        </label>
        <label class="stack">
          ${fieldLabel('25Live reservations URL', 'Use a 25Live rm_reservations.xml URL. The app will keep space_id matched to the room ID and preserve date query values.')}
          <input type="text" value="${escapeHtml(roomSign.feed_url ?? '')}" data-global-field="room_sign.feed_url" placeholder="https://25live.collegenet.com/25live/data/utk/run/rm_reservations.xml?caller=pro&space_id=1536&start_dt=-30&end_dt=%2B180&options=standard" />
        </label>
        <label class="stack">
          ${fieldLabel('Calendar web name', 'Optional fallback for published 25Live/Trumba JSON feeds. Leave blank when using the reservations URL above.')}
          <input type="text" value="${escapeHtml(roomSign.calendar_web_name ?? '')}" data-global-field="room_sign.calendar_web_name" placeholder="yourcalendarwebname" />
        </label>
        <label class="stack">
          ${fieldLabel('Timezone', 'Timezone used to format event dates and times on the sign.')}
          <input type="text" value="${escapeHtml(roomSign.timezone ?? 'America/New_York')}" data-global-field="room_sign.timezone" />
        </label>
        <label class="stack">
          ${fieldLabel('Lookahead days', 'How many days ahead to display when the sign is not on air or recording.')}
          <input type="number" min="1" max="31" value="${escapeHtml(roomSign.lookahead_days ?? 7)}" data-global-field="room_sign.lookahead_days" />
        </label>
        <label class="stack">
          ${fieldLabel('Max events', 'Maximum number of upcoming events shown in schedule mode.')}
          <input type="number" min="1" max="20" value="${escapeHtml(roomSign.max_events ?? 6)}" data-global-field="room_sign.max_events" />
        </label>
        <label class="stack">
          ${fieldLabel('Refresh seconds', 'How often the app refreshes 25Live schedule data. 60 seconds is a practical default.')}
          <input type="number" min="15" max="3600" value="${escapeHtml(roomSign.refresh_seconds ?? 60)}" data-global-field="room_sign.refresh_seconds" />
        </label>
      </div>
    </article>
    `)}

    ${tabPanel('companion', `
    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Companion source</h3>
          <p>Read PGM, PVW, and per-mic anchor assignments from Companion or vMix variables.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          ${fieldLabel('Enable Companion polling', 'Turn this on when the Pi should read values from Companion HTTP variable endpoints.')}
          <select data-global-field="companion.enabled">
            <option value="true" ${companion.enabled ? 'selected' : ''}>true</option>
            <option value="false" ${!companion.enabled ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Companion base URL', 'The web address for Companion on the machine running it, for example http://10.0.0.50:8000.')}
          <input type="text" value="${escapeHtml(companion.base_url ?? 'http://127.0.0.1:8000')}" data-global-field="companion.base_url" />
        </label>
        <label class="stack">
          ${fieldLabel('Default connection label', 'The Companion instance label used when a variable is entered without a prefix. For vMix variables this is often vmix.')}
          <input type="text" value="${escapeHtml(companion.connection_label ?? 'Cuez')}" data-global-field="companion.connection_label" />
        </label>
        <label class="stack">
          ${fieldLabel('Show title variable', 'Legacy title variable. Most setups can leave this blank now that the kiosk uses PGM and PVW.')}
          <input type="text" value="${escapeHtml(companion.variable_name ?? '')}" data-global-field="companion.variable_name" placeholder="segment_title" />
        </label>
        <label class="stack">
          ${fieldLabel('PGM / Now source variable', 'Variable shown in the green Now box. Example: vmix:mix_1_program_full_title or $(vmix:mix_1_program_full_title).')}
          <input type="text" value="${escapeHtml(companion.on_air_source_variable_name ?? '')}" data-global-field="companion.on_air_source_variable_name" placeholder="CurrentSource" />
        </label>
        <label class="stack">
          ${fieldLabel('PVW / Next source variable', 'Variable shown in the yellow Next box. Enter the vMix preview variable name here.')}
          <input type="text" value="${escapeHtml(companion.next_source_variable_name ?? '')}" data-global-field="companion.next_source_variable_name" placeholder="NextSource" />
        </label>
        <label class="stack">
          ${fieldLabel('Status sign variable', 'Variable for the right-side neon sign. Values like On Air, ON_AIR, Recording, or REC use the built-in graphics; any other value displays as custom neon text.')}
          <input type="text" value="${escapeHtml(companion.status_sign_variable_name ?? '')}" data-global-field="companion.status_sign_variable_name" placeholder="ProductionStatus" />
        </label>
      </div>
    </article>
    `)}

    ${tabPanel('photos', `
    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Anchor photos</h3>
          <p>Match anchor names to headshots, such as JohnSmith.png.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          ${fieldLabel('Enable photos', 'Turn on headshots beside mic names on the fullscreen display.')}
          <select data-global-field="anchor_photos.enabled">
            <option value="true" ${anchorPhotos.enabled ? 'selected' : ''}>true</option>
            <option value="false" ${!anchorPhotos.enabled ? 'selected' : ''}>false</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Windows share path', 'Optional SMB path. HTTP folder URL is usually easier and more reliable.')}
          <input type="text" value="${escapeHtml(anchorPhotos.share_path ?? '')}" data-global-field="anchor_photos.share_path" placeholder="\\\\servername\\folder" />
        </label>
        <label class="stack">
          ${fieldLabel('HTTP folder URL', 'Recommended photo method. Point this to a simple web folder on the vMix or Companion computer.')}
          <input type="text" value="${escapeHtml(anchorPhotos.base_url ?? '')}" data-global-field="anchor_photos.base_url" placeholder="http://vmix-host:8090/" />
        </label>
        <label class="stack">
          ${fieldLabel('Username', 'Only needed for a protected Windows share. Leave blank for HTTP photo hosting.')}
          <input type="text" value="${escapeHtml(anchorPhotos.username ?? '')}" data-global-field="anchor_photos.username" />
        </label>
        <label class="stack">
          ${fieldLabel('Password', 'Only needed for a protected Windows share. Leave blank for HTTP photo hosting.')}
          <input type="password" value="${escapeHtml(anchorPhotos.password ?? '')}" data-global-field="anchor_photos.password" />
        </label>
        <label class="stack">
          ${fieldLabel('Domain', 'Optional Windows domain or computer name for SMB authentication.')}
          <input type="text" value="${escapeHtml(anchorPhotos.domain ?? '')}" data-global-field="anchor_photos.domain" />
        </label>
        <label class="stack">
          ${fieldLabel('Timeout seconds', 'How long the Pi waits for a photo lookup before drawing the mic without a picture.')}
          <input type="number" min="1" max="30" value="${escapeHtml(anchorPhotos.timeout_seconds ?? 4)}" data-global-field="anchor_photos.timeout_seconds" />
        </label>
      </div>
    </article>
    `)}

    ${tabPanel('receivers', `
    <article class="config-card">
      <div class="config-card-head">
        <div>
          <h3>Receiver defaults</h3>
          <p>QLX-D default connection settings and optional auth for System API mode.</p>
        </div>
      </div>
      <div class="config-card-grid">
        <label class="stack">
          ${fieldLabel('Auth type', 'Leave as none for normal QLX-D receiver polling. Bearer is for custom System API integrations.')}
          <select data-global-field="auth.type">
            <option value="none" ${String(auth.type || 'none') === 'none' ? 'selected' : ''}>none</option>
            <option value="bearer" ${String(auth.type || '') === 'bearer' ? 'selected' : ''}>bearer</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Default scheme', 'Use tcp for QLX-D receivers. HTTP/HTTPS are for custom API integrations.')}
          <select data-global-field="default_connection.scheme">
            <option value="tcp" ${defaults.scheme === 'tcp' ? 'selected' : ''}>tcp</option>
            <option value="http" ${defaults.scheme === 'http' ? 'selected' : ''}>http</option>
            <option value="https" ${defaults.scheme === 'https' ? 'selected' : ''}>https</option>
          </select>
        </label>
        <label class="stack">
          ${fieldLabel('Default port', 'QLX-D control normally uses TCP port 2202.')}
          <input type="number" min="1" max="65535" value="${escapeHtml(defaults.port ?? 2202)}" data-global-field="default_connection.port" />
        </label>
        <label class="stack">
          ${fieldLabel('Token URL', 'Only used for bearer auth in System API mode.')}
          <input type="text" value="${escapeHtml(auth.token_url ?? '')}" data-global-field="auth.token_url" />
        </label>
        <label class="stack">
          ${fieldLabel('Client ID', 'Only used for bearer auth in System API mode.')}
          <input type="text" value="${escapeHtml(auth.client_id ?? '')}" data-global-field="auth.client_id" />
        </label>
        <label class="stack">
          ${fieldLabel('Client secret', 'Only used for bearer auth in System API mode.')}
          <input type="password" value="${escapeHtml(auth.client_secret ?? '')}" data-global-field="auth.client_secret" />
        </label>
        <label class="stack">
          ${fieldLabel('Grant type', 'OAuth grant type for System API mode. Leave as client_credentials unless your API requires something else.')}
          <input type="text" value="${escapeHtml(auth.grant_type ?? 'client_credentials')}" data-global-field="auth.grant_type" />
        </label>
      </div>
    </article>
    `)}
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
  const fps = Number.isFinite(Number(ndiStatus.actual_fps)) ? ` | Actual FPS: ${Number(ndiStatus.actual_fps).toFixed(1)}` : ''
  const error = ndiStatus.last_error ? ` Error: ${escapeHtml(ndiStatus.last_error)}` : ''
  return `Status: ${escapeHtml(ndiStatus.connection_status || 'unknown')} | Source: ${escapeHtml(source)} | Frame: ${escapeHtml(frame)}${fps}${error}`
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
              ${fieldLabel('Mic ID', 'Stable internal ID for this tile. Keep it unique, such as mic-1.')}
              <input type="text" value="${escapeHtml(mic.id)}" data-mic-index="${index}" data-mic-field="id" />
            </label>
            <label class="stack">
              ${fieldLabel('Display label', 'Fallback label when there is no assigned anchor name from Companion.')}
              <input type="text" value="${escapeHtml(mic.default_name)}" data-mic-index="${index}" data-mic-field="default_name" />
            </label>
            <label class="stack">
              ${fieldLabel('Assigned to', 'Manual name for this mic. Companion assignment variables override this when configured.')}
              <input type="text" value="${escapeHtml(mic.assigned_to ?? '')}" data-mic-index="${index}" data-mic-field="assigned_to" placeholder="Lead Anchor" />
            </label>
            <label class="stack">
              ${fieldLabel('Companion assignment variable', 'Variable that returns the person assigned to this mic, for example mic_1_anchor or $(custom:Mic1).')}
              <input type="text" value="${escapeHtml(mic.assignment_variable_name ?? '')}" data-mic-index="${index}" data-mic-field="assignment_variable_name" placeholder="mic_1_anchor" />
            </label>
            <label class="stack">
              ${fieldLabel('Receiver label', 'Friendly label for the receiver rack or location.')}
              <input type="text" value="${escapeHtml(mic.receiver_name ?? '')}" data-mic-index="${index}" data-mic-field="receiver_name" />
            </label>
            <label class="stack">
              ${fieldLabel('Channel', 'Friendly channel label shown in the dashboard and under assigned names.')}
              <input type="text" value="${escapeHtml(mic.channel_label ?? '')}" data-mic-index="${index}" data-mic-field="channel_label" />
            </label>
            <label class="stack">
              ${fieldLabel('Receiver channel', 'Usually 1 for a single-channel QLX-D receiver.')}
              <input type="number" min="1" max="4" value="${escapeHtml(mic.receiver_channel ?? 1)}" data-mic-index="${index}" data-mic-field="receiver_channel" />
            </label>
            <label class="stack">
              ${fieldLabel('Device IP / host', 'IP address or hostname of the Shure receiver, not the transmitter.')}
              <input type="text" value="${escapeHtml(mic.device_ip ?? '')}" data-mic-index="${index}" data-mic-field="device_ip" placeholder="192.168.1.40" />
            </label>
            <label class="stack">
              ${fieldLabel('Scheme', 'Use tcp for normal QLX-D receiver polling.')}
              <select data-mic-index="${index}" data-mic-field="scheme">
                <option value="tcp" ${mic.scheme === 'tcp' ? 'selected' : ''}>tcp</option>
                <option value="http" ${mic.scheme === 'http' ? 'selected' : ''}>http</option>
                <option value="https" ${mic.scheme === 'https' ? 'selected' : ''}>https</option>
              </select>
            </label>
            <label class="stack">
              ${fieldLabel('Port', 'QLX-D control normally uses 2202.')}
              <input type="number" min="1" max="65535" value="${escapeHtml(mic.port ?? configState.default_connection.port ?? 443)}" data-mic-index="${index}" data-mic-field="port" />
            </label>
            <label class="stack">
              ${fieldLabel('Telemetry path', 'Only used for HTTP/System API mode. Leave blank for QLX-D tcp mode.')}
              <input type="text" value="${escapeHtml(mic.telemetry_path ?? '')}" data-mic-index="${index}" data-mic-field="telemetry_path" placeholder="/api/receivers/rack-a/channels/a1" />
            </label>
            <label class="stack">
              ${fieldLabel('Rename path', 'Only used for HTTP/System API mode. Leave blank for QLX-D tcp mode.')}
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
  micConfigSectionEl.classList.toggle('is-active', activeConfigTab === 'mics')
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
    assignment_variable_name: '',
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
      now_panel_enabled: configState.display.now_panel_enabled !== false,
      now_panel_label: String(configState.display.now_panel_label || 'Now').trim() || 'Now',
      now_panel_border_color: normalizeHexColor(configState.display.now_panel_border_color, '#1cff00'),
      next_panel_enabled: configState.display.next_panel_enabled !== false,
      next_panel_label: String(configState.display.next_panel_label || 'Next').trim() || 'Next',
      next_panel_border_color: normalizeHexColor(configState.display.next_panel_border_color, '#fff200'),
      status_sign_enabled: configState.display.status_sign_enabled !== false,
      status_sign_custom_text: String(configState.display.status_sign_custom_text || '').trim(),
    },
    companion: {
      enabled: Boolean(configState.companion.enabled),
      base_url: String(configState.companion.base_url || 'http://127.0.0.1:8000').trim(),
      connection_label: String(configState.companion.connection_label || 'Cuez').trim(),
      variable_name: String(configState.companion.variable_name || '').trim(),
      on_air_source_variable_name: String(configState.companion.on_air_source_variable_name || '').trim(),
      next_source_variable_name: String(configState.companion.next_source_variable_name || '').trim(),
      status_sign_variable_name: String(configState.companion.status_sign_variable_name || '').trim(),
    },
    room_sign: {
      enabled: Boolean(configState.room_sign.enabled),
      room_name: String(configState.room_sign.room_name || 'Studio').trim() || 'Studio',
      room_id: String(configState.room_sign.room_id || '').trim(),
      feed_url: String(configState.room_sign.feed_url || '').trim(),
      calendar_web_name: String(configState.room_sign.calendar_web_name || '').trim(),
      timezone: String(configState.room_sign.timezone || 'America/New_York').trim() || 'America/New_York',
      lookahead_days: Number(configState.room_sign.lookahead_days || 7),
      max_events: Number(configState.room_sign.max_events || 6),
      refresh_seconds: Number(configState.room_sign.refresh_seconds || 60),
    },
    anchor_photos: {
      enabled: Boolean(configState.anchor_photos.enabled),
      base_url: String(configState.anchor_photos.base_url || '').trim(),
      share_path: String(configState.anchor_photos.share_path || '').trim(),
      username: String(configState.anchor_photos.username || '').trim(),
      password: String(configState.anchor_photos.password || ''),
      domain: String(configState.anchor_photos.domain || '').trim(),
      timeout_seconds: Number(configState.anchor_photos.timeout_seconds || 4),
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
      assignment_variable_name: String(mic.assignment_variable_name || '').trim(),
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
    activeConfigTab = 'mics'
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
    return
  }

  const tabButton = target.closest('[data-config-tab]')
  if (tabButton instanceof HTMLElement) {
    activeConfigTab = tabButton.dataset.configTab || 'display'
    render()
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
