const statusViewEl = document.getElementById('statusView')
const scheduleViewEl = document.getElementById('scheduleView')
const statusTextEl = document.getElementById('statusText')
const currentEventTitleEl = document.getElementById('currentEventTitle')
const currentEventMetaEl = document.getElementById('currentEventMeta')
const scheduleRoomNameEl = document.getElementById('scheduleRoomName')
const clockTextEl = document.getElementById('clockText')
const eventListEl = document.getElementById('eventList')
const roomFallbackEl = document.getElementById('roomFallback')
const scheduleErrorEl = document.getElementById('scheduleError')

const REFRESH_MS = 1000

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function statusFontSize(text) {
  const length = String(text || '').trim().length
  if (length >= 16) return 'clamp(4rem, 9vw, 10rem)'
  if (length >= 11) return 'clamp(5.8rem, 13vw, 15rem)'
  return ''
}

function updateClock() {
  const now = new Date()
  clockTextEl.textContent = now.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function eventMeta(event) {
  if (!event) return ''
  return `${event.date_label || ''} | ${event.time_label || ''}`.trim()
}

function renderStatusMode(state) {
  const text = String(state.status_text || '').trim().toUpperCase()
  const fontSize = statusFontSize(text)
  statusTextEl.textContent = text || 'ON AIR'
  if (fontSize) {
    statusTextEl.style.setProperty('--status-font-size', fontSize)
  } else {
    statusTextEl.style.removeProperty('--status-font-size')
  }

  if (state.current_event) {
    currentEventTitleEl.textContent = state.current_event.title || state.room_name || 'Current Event'
    currentEventMetaEl.textContent = eventMeta(state.current_event)
  } else {
    currentEventTitleEl.textContent = state.room_name || 'Studio'
    currentEventMetaEl.textContent = 'No current 25Live event'
  }

  statusViewEl.classList.add('is-active')
  scheduleViewEl.classList.remove('is-active')
}

function renderScheduleEvent(event) {
  return `
    <article class="schedule-event">
      <div class="schedule-event-date">${escapeHtml(event.date_label || '')}</div>
      <div class="schedule-event-title">${escapeHtml(event.title || 'Untitled Event')}</div>
      <div class="schedule-event-time">${escapeHtml(event.time_label || '')}</div>
    </article>
  `
}

function renderScheduleMode(state) {
  const events = Array.isArray(state.upcoming_events) ? state.upcoming_events : []
  scheduleRoomNameEl.textContent = state.room_name || 'Studio'
  scheduleErrorEl.textContent = state.schedule_error || ''
  eventListEl.innerHTML = events.map(renderScheduleEvent).join('')
  eventListEl.style.display = events.length ? 'grid' : 'none'
  roomFallbackEl.textContent = state.room_name || 'Studio'
  roomFallbackEl.classList.toggle('is-active', !events.length)

  scheduleViewEl.classList.add('is-active')
  statusViewEl.classList.remove('is-active')
}

function render(state) {
  if (state.is_status_active) {
    renderStatusMode(state)
  } else {
    renderScheduleMode(state)
  }
}

async function fetchState() {
  const response = await fetch('/api/room-sign/state', { cache: 'no-store' })
  if (!response.ok) {
    throw new Error('Failed to load room sign state')
  }
  render(await response.json())
}

async function tick() {
  updateClock()
  try {
    await fetchState()
  } catch (error) {
    scheduleErrorEl.textContent = error.message || 'Room sign unavailable'
    statusViewEl.classList.remove('is-active')
    scheduleViewEl.classList.add('is-active')
  }
}

tick()
window.setInterval(tick, REFRESH_MS)
