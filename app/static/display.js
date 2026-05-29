const clockTimeEl = document.getElementById('clockTime')
const showDateEl = document.getElementById('showDate')
const showTitleEl = document.getElementById('showTitle')
const onAirSourceEl = document.getElementById('onAirSource')
const previewFrameEl = document.getElementById('previewFrame')
const micStripEl = document.getElementById('micStrip')

let refreshHandle = null
let clockHandle = null
let ndiPreviewHandle = null
let ndiPreviewAbort = null
let ndiPreviewObjectUrl = ''
let previewSignature = ''
let lastFontFamily = ''

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function titleCaseFallback(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\b\w/g, (match) => match.toUpperCase())
}

function errorText(error) {
  return titleCaseFallback(error?.message || error || 'Unavailable')
}

function updateClock() {
  const now = new Date()
  clockTimeEl.textContent = now.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  })
  showDateEl.textContent = now
    .toLocaleDateString([], {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
    .toUpperCase()
}

function batteryBars(percent) {
  const level = Math.max(0, Math.min(5, Math.round(Number(percent || 0) / 20)))
  return Array.from({ length: 5 }, (_, index) => index < level)
}

function tileStatusMessage(mic) {
  if (!mic.is_online) return 'OFF'
  if (Array.isArray(mic.errors) && mic.errors.length) return String(mic.errors[0] || '').toUpperCase()
  if (Number(mic.battery_percent || 0) <= 20) return 'LOW BATTERY'
  return ''
}

function batteryMarkup(mic) {
  const bars = batteryBars(mic.battery_percent)
  return `
    <div class="battery-visual">
      <div class="battery-shell">
        ${bars
          .map(
            (isOn) =>
              `<span class="battery-bar ${isOn ? `is-on ${escapeHtml(mic.health)}` : ''}"></span>`,
          )
          .join('')}
      </div>
      <span class="battery-cap"></span>
      <span class="battery-percent">${escapeHtml(`${Math.round(Number(mic.battery_percent || 0))}%`)}</span>
    </div>
  `
}

function photoDataAttributes(urls) {
  return escapeHtml(JSON.stringify(urls || []))
}

function nameFontSize(name) {
  const length = String(name || '').length
  if (length >= 24) return 'clamp(1rem, 1.2vw, 1.55rem)'
  if (length >= 18) return 'clamp(1.08rem, 1.35vw, 1.8rem)'
  if (length >= 14) return 'clamp(1.2rem, 1.55vw, 2.05rem)'
  return ''
}

function renderMicTiles(mics) {
  if (!Array.isArray(mics) || !mics.length) {
    micStripEl.innerHTML = `
      <article class="mic-tile offline">
        <h2 class="mic-title">No Mics</h2>
        <div class="mic-main">
          <div class="mic-message">Waiting For Receiver Data</div>
        </div>
      </article>
    `
    return
  }

  micStripEl.innerHTML = mics
    .map((mic, index) => {
      const message = tileStatusMessage(mic)
      const title = mic.assigned_to || mic.display_name || `Mic ${index + 1}`
      const subtitle = mic.assigned_to
        ? mic.display_name || mic.channel_label || mic.receiver_name || `Mic ${index + 1}`
        : mic.channel_label || mic.receiver_name || `Mic ${index + 1}`
      const main = message
        ? `<div class="mic-message">${escapeHtml(message)}</div>`
        : batteryMarkup(mic)
      const photoUrls = Array.isArray(mic.anchor_photo_urls) && mic.anchor_photo_urls.length
        ? mic.anchor_photo_urls.map(String)
        : [String(mic.anchor_photo_url || '')].filter(Boolean)
      const photoUrl = photoUrls[0] || ''
      const photoMarkup = photoUrl
        ? `<img class="anchor-photo" src="${escapeHtml(photoUrl)}" alt="${escapeHtml(title)}" data-photo-urls="${photoDataAttributes(photoUrls)}" data-photo-index="0" onerror="handleAnchorPhotoError(this);" />`
        : ''
      const personClass = photoUrl ? 'has-photo' : 'no-photo'
      const fontSize = nameFontSize(title)
      const fontStyle = fontSize ? ` style="--name-font-size: ${escapeHtml(fontSize)}"` : ''
      return `
        <article class="mic-tile ${escapeHtml(mic.health)} ${personClass}">
          ${photoMarkup}
          <div class="mic-content">
            <div class="mic-person">
              <div class="mic-person-text"${fontStyle}>
                <h2 class="mic-title">${escapeHtml(title)}</h2>
                <div class="mic-subtitle">${escapeHtml(subtitle)}</div>
              </div>
            </div>
            <div class="mic-main">${main}</div>
            <div class="mic-stats">
              <span>BAT ${escapeHtml(`${Math.round(Number(mic.battery_percent || 0))}%`)}</span>
              <span>RF ${escapeHtml(`${Math.round(Number(mic.signal_strength || 0))}%`)}</span>
              <span>AUD ${escapeHtml(`${Math.round(Number(mic.audio_level || 0))}%`)}</span>
            </div>
          </div>
        </article>
      `
    })
    .join('')
}

function handleAnchorPhotoError(img) {
  const urls = JSON.parse(img.dataset.photoUrls || '[]')
  const nextIndex = Number(img.dataset.photoIndex || 0) + 1
  if (urls[nextIndex]) {
    img.dataset.photoIndex = String(nextIndex)
    img.src = urls[nextIndex]
    return
  }
  img.closest('.mic-tile')?.classList.remove('has-photo')
  img.closest('.mic-tile')?.classList.add('no-photo')
  img.remove()
}

window.handleAnchorPhotoError = handleAnchorPhotoError

function renderPreview(display) {
  const previewMode = String(display.preview_mode || 'placeholder')
  const previewUrl = String(display.preview_url || '')
  const sourceName = String(display.preview_source_name || '').trim()
  const posterUrl = String(display.preview_poster_url || '')
  const signature = JSON.stringify([previewMode, previewUrl, sourceName, posterUrl])

  if (signature === previewSignature) return
  previewSignature = signature
  stopNdiPreview()

  if (previewMode === 'ndi') {
    if (sourceName) {
      previewFrameEl.innerHTML = '<img id="ndiPreviewImage" alt="NDI preview feed" />'
      startNdiPreview()
      return
    }
  }

  if (!previewUrl || previewMode === 'placeholder') {
    previewFrameEl.innerHTML = `
      <div class="preview-placeholder">
        <div>
          <strong>${escapeHtml(sourceName || 'NDI PREVIEW')}</strong>
          <span>Set a browser-playable preview URL on the config page for this source.</span>
        </div>
      </div>
    `
    return
  }

  if (previewMode === 'image') {
    previewFrameEl.innerHTML = `<img src="${escapeHtml(previewUrl)}" alt="Preview feed" />`
    return
  }

  if (previewMode === 'video') {
    previewFrameEl.innerHTML = `<video src="${escapeHtml(previewUrl)}" poster="${escapeHtml(posterUrl)}" autoplay muted playsinline></video>`
    return
  }

  previewFrameEl.innerHTML = `<iframe src="${escapeHtml(previewUrl)}" title="Preview feed" allow="autoplay; fullscreen"></iframe>`
}

function stopNdiPreview() {
  if (ndiPreviewHandle) {
    window.clearTimeout(ndiPreviewHandle)
    ndiPreviewHandle = null
  }
  if (ndiPreviewAbort) {
    ndiPreviewAbort.abort()
    ndiPreviewAbort = null
  }
  if (ndiPreviewObjectUrl) {
    URL.revokeObjectURL(ndiPreviewObjectUrl)
    ndiPreviewObjectUrl = ''
  }
}

function startNdiPreview() {
  const img = document.getElementById('ndiPreviewImage')
  if (!(img instanceof HTMLImageElement)) return

  const pullFrame = async () => {
    ndiPreviewAbort = new AbortController()
    try {
      const response = await fetch(`/api/ndi/latest.jpg?t=${Date.now()}`, {
        cache: 'no-store',
        signal: ndiPreviewAbort.signal,
      })
      if (response.ok) {
        const blob = await response.blob()
        const nextUrl = URL.createObjectURL(blob)
        const previousUrl = ndiPreviewObjectUrl
        img.src = nextUrl
        ndiPreviewObjectUrl = nextUrl
        if (previousUrl) {
          window.setTimeout(() => URL.revokeObjectURL(previousUrl), 1000)
        }
      }
    } catch (error) {
      if (error?.name !== 'AbortError') console.warn(errorText(error))
    } finally {
      ndiPreviewAbort = null
      if (document.getElementById('ndiPreviewImage') === img) {
        ndiPreviewHandle = window.setTimeout(pullFrame, 20)
      }
    }
  }

  pullFrame()
}

function renderState(state) {
  const display = state.display || {}
  const titleText = String(display.show_title || display.manual_show_title || 'Anchor Mics').trim()
  showTitleEl.textContent = titleText.toUpperCase()
  onAirSourceEl.textContent = String(display.on_air_source_name || '').trim().toUpperCase()
  renderPreview(display)
  renderMicTiles(state.mics || [])

  const fontFamily = String(display.font_family || '').trim()
  if (fontFamily && fontFamily !== lastFontFamily) {
    document.documentElement.style.setProperty('--display-font', fontFamily)
    lastFontFamily = fontFamily
  }
}

async function fetchState() {
  const response = await fetch('/api/state')
  if (!response.ok) {
    throw new Error('Failed to load display state')
  }
  const state = await response.json()
  renderState(state)
}

async function start() {
  updateClock()
  clockHandle = window.setInterval(updateClock, 1000)

  try {
    await fetchState()
  } catch (error) {
    showTitleEl.textContent = 'ANCHOR MICS'
    onAirSourceEl.textContent = errorText(error)
    renderPreview({ preview_mode: 'placeholder', preview_source_name: 'Preview unavailable' })
    renderMicTiles([])
  }

  refreshHandle = window.setInterval(() => {
    fetchState().catch((error) => {
      onAirSourceEl.textContent = errorText(error)
    })
  }, 2000)
}

window.addEventListener('beforeunload', () => {
  if (refreshHandle) window.clearInterval(refreshHandle)
  if (clockHandle) window.clearInterval(clockHandle)
  stopNdiPreview()
})

start()
