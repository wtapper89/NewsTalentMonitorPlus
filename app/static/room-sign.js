const statusViewEl = document.getElementById('statusView')
const scheduleViewEl = document.getElementById('scheduleView')
const statusTextEl = document.getElementById('statusText')
const currentEventTitleEl = document.getElementById('currentEventTitle')
const currentEventMetaEl = document.getElementById('currentEventMeta')
const statusWordEl = statusTextEl.closest('.status-word')
const scheduleRoomNameEl = document.getElementById('scheduleRoomName')
const clockTextEl = document.getElementById('clockText')
const eventListEl = document.getElementById('eventList')
const roomFallbackEl = document.getElementById('roomFallback')
const scheduleErrorEl = document.getElementById('scheduleError')
const availabilityPillEl = document.getElementById('availabilityPill')

const REFRESH_MS = 1000
let eventsMarkup = null
let titleFitFrame = null

function fitEventTitles() {
  titleFitFrame = null
  if (!scheduleViewEl.classList.contains('is-active')) return
  const titles = [...eventListEl.querySelectorAll('.schedule-event-title')]
  if (!titles.length) return
  let low = 1
  let high = Math.max(...titles.map(title => title.parentElement.clientHeight))
  // One shared size: the most constrained title determines every card's size.
  for (let i = 0; i < 16; i += 1) {
    const size = (low + high) / 2
    eventListEl.style.setProperty('--event-title-size', `${size}px`)
    const fits = titles.every(title => {
      const space = title.parentElement
      return title.getBoundingClientRect().height <= space.clientHeight - 2
        && title.scrollWidth <= space.clientWidth
    })
    if (fits) low = size
    else high = size
  }
  eventListEl.style.setProperty('--event-title-size', `${Math.floor(low)}px`)
}

function scheduleTitleFit() {
  if (titleFitFrame === null) titleFitFrame = requestAnimationFrame(fitEventTitles)
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function fitStatusText() {
  if (!statusViewEl.classList.contains('is-active')) return

  const footerBounds = statusViewEl.querySelector('.event-footer').getBoundingClientRect()
  const statusStyles = window.getComputedStyle(statusViewEl)
  const horizontalPadding = parseFloat(statusStyles.paddingLeft) + parseFloat(statusStyles.paddingRight)
  const verticalPadding = parseFloat(statusStyles.paddingTop) + parseFloat(statusStyles.paddingBottom)
  const maxWidth = Math.max(1, (window.innerWidth - horizontalPadding) * 0.98)
  const maxHeight = Math.max(1, (window.innerHeight - footerBounds.height - verticalPadding) * 0.98)
  let low = 24
  let high = Math.max(240, maxHeight * 3)

  for (let i = 0; i < 18; i += 1) {
    const size = (low + high) / 2
    statusTextEl.style.fontSize = `${size}px`
    const textBounds = statusTextEl.getBoundingClientRect()
    const fits = textBounds.width <= maxWidth && textBounds.height <= maxHeight
    if (fits) {
      low = size
    } else {
      high = size
    }
  }
  statusTextEl.style.fontSize = `${Math.floor(low)}px`
  console.debug('status fit', {
    text: statusTextEl.textContent,
    fontSize: Math.floor(low),
    maxWidth,
    maxHeight,
  })
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
  statusTextEl.textContent = text || 'ON AIR'
  const mode = String(state.status_mode || '').trim()
  const isHot = mode === 'on-air' || mode === 'recording'

  if (state.current_event) {
    currentEventTitleEl.textContent = state.current_event.title || state.room_name || 'Current Event'
    currentEventMetaEl.textContent = eventMeta(state.current_event)
  } else {
    currentEventTitleEl.textContent = state.room_name || 'Studio'
    currentEventMetaEl.textContent = 'No current 25Live event'
  }

  statusViewEl.classList.add('is-active')
  statusViewEl.classList.toggle('status-hot', isHot)
  scheduleViewEl.classList.remove('is-active', 'is-available', 'is-in-use')
  window.requestAnimationFrame(fitStatusText)
}

function renderScheduleEvent(event) {
  const isCurrent = Boolean(event && event.is_current)
  return `
    <article class="schedule-event${isCurrent ? ' is-current' : ''}">
      <header class="schedule-event-heading">
        <div class="schedule-event-date">${escapeHtml(event.date_label || (isCurrent ? 'Today' : ''))}</div>
        <div class="schedule-event-time">${escapeHtml(event.time_label || '')}</div>
      </header>
      <div class="schedule-event-title-space"><div class="schedule-event-title">${escapeHtml(event.title || 'Untitled Event')}</div></div>
    </article>
  `
}

function renderScheduleMode(state) {
  const isInUse = Boolean(state.current_event)
  const events = [
    ...(isInUse ? [{ ...state.current_event, is_current: true }] : []),
    ...(Array.isArray(state.upcoming_events) ? state.upcoming_events : []),
  ]
  scheduleRoomNameEl.textContent = state.room_name || 'Studio'
  scheduleErrorEl.textContent = state.schedule_error || ''
  const markup = events.map(renderScheduleEvent).join('')
  const changed = markup !== eventsMarkup
  const wasHidden = !scheduleViewEl.classList.contains('is-active')
  if (changed) {
    eventListEl.innerHTML = markup
    eventsMarkup = markup
  }
  eventListEl.style.display = events.length ? 'grid' : 'none'
  roomFallbackEl.textContent = 'No upcoming events'
  roomFallbackEl.classList.toggle('is-active', !events.length)
  availabilityPillEl.textContent = isInUse ? 'In Use' : 'Available'

  scheduleViewEl.classList.add('is-active')
  scheduleViewEl.classList.toggle('is-in-use', isInUse)
  scheduleViewEl.classList.toggle('is-available', !isInUse)
  statusViewEl.classList.remove('is-active', 'status-hot')
  if (changed || wasHidden) scheduleTitleFit()
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
    scheduleViewEl.classList.add('is-available')
    scheduleViewEl.classList.remove('is-in-use')
    statusViewEl.classList.remove('is-active')
    scheduleViewEl.classList.add('is-active')
  }
}

window.addEventListener('resize', fitStatusText)
window.addEventListener('resize', scheduleTitleFit)
new ResizeObserver(scheduleTitleFit).observe(eventListEl)
document.fonts.ready.then(scheduleTitleFit)

tick()
window.setInterval(tick, REFRESH_MS)
