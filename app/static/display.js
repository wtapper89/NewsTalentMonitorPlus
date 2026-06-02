const clockTimeEl = document.getElementById('clockTime')
const nowSourceEl = document.getElementById('nowSource')
const nextSourceEl = document.getElementById('nextSource')
const previewFrameEl = document.getElementById('previewFrame')
const micStripEl = document.getElementById('micStrip')

let refreshHandle = null
let clockHandle = null
let ndiPreviewHandle = null
let ndiPreviewAbort = null
let ndiPreviewObjectUrl = ''
let ndiLastFrameAt = 0
let previewSignature = ''
let lastFontFamily = ''
const loadedPhotoUrls = new Map()
const missingPhotoSignatures = new Map()
const MISSING_PHOTO_RETRY_MS = 60000
const DISPLAY_STATE_REFRESH_MS = 500

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
}

function batteryBars(percent) {
  const level = Math.max(0, Math.min(5, Math.round(Number(percent || 0) / 20)))
  return Array.from({ length: 5 }, (_, index) => index < level)
}

function tileStatusMessage(mic) {
  if (!mic.is_online) return 'OFF'
  if (Array.isArray(mic.errors) && mic.errors.length) return String(mic.errors[0] || '').toUpperCase()
  if (Number(mic.battery_percent || 0) <= 10) return 'LOW BATTERY'
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

function photoSignature(urls) {
  return JSON.stringify((urls || []).filter(Boolean))
}

function shouldSkipPhoto(signature) {
  const failedAt = missingPhotoSignatures.get(signature)
  if (!failedAt) return false
  if (Date.now() - failedAt > MISSING_PHOTO_RETRY_MS) {
    missingPhotoSignatures.delete(signature)
    return false
  }
  return true
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
      const signature = photoSignature(photoUrls)
      const skipPhoto = signature ? shouldSkipPhoto(signature) : true
      const loadedPhotoUrl = signature ? loadedPhotoUrls.get(signature) || '' : ''
      const photoUrl = loadedPhotoUrl || (!skipPhoto ? photoUrls[0] || '' : '')
      const photoLoaded = Boolean(loadedPhotoUrl)
      const photoMarkup = photoUrl
        ? `<img class="anchor-photo ${photoLoaded ? '' : 'pending'}" src="${escapeHtml(photoUrl)}" alt="${escapeHtml(title)}" data-photo-signature="${escapeHtml(signature)}" data-photo-urls="${photoDataAttributes(photoUrls)}" data-photo-index="0" onload="handleAnchorPhotoLoad(this);" onerror="handleAnchorPhotoError(this);" />`
        : ''
      const personClass = photoLoaded ? 'has-photo' : 'no-photo'
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

function handleAnchorPhotoLoad(img) {
  const signature = img.dataset.photoSignature || ''
  if (signature) {
    loadedPhotoUrls.set(signature, img.currentSrc || img.src)
    missingPhotoSignatures.delete(signature)
  }
  img.classList.remove('pending')
  img.closest('.mic-tile')?.classList.remove('no-photo')
  img.closest('.mic-tile')?.classList.add('has-photo')
}

function handleAnchorPhotoError(img) {
  const urls = JSON.parse(img.dataset.photoUrls || '[]')
  const nextIndex = Number(img.dataset.photoIndex || 0) + 1
  if (urls[nextIndex]) {
    img.dataset.photoIndex = String(nextIndex)
    img.src = urls[nextIndex]
    return
  }
  const signature = img.dataset.photoSignature || photoSignature(urls)
  if (signature) {
    loadedPhotoUrls.delete(signature)
    missingPhotoSignatures.set(signature, Date.now())
  }
  img.closest('.mic-tile')?.classList.add('no-photo')
  img.closest('.mic-tile')?.classList.remove('has-photo')
  img.remove()
}

window.handleAnchorPhotoLoad = handleAnchorPhotoLoad
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
      previewFrameEl.innerHTML = `<img id="ndiPreviewImage" src="/api/ndi/preview.mjpg?t=${Date.now()}" alt="NDI preview feed" />`
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
  ndiLastFrameAt = 0
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
        ndiLastFrameAt = Date.now()
        if (previousUrl) {
          window.setTimeout(() => URL.revokeObjectURL(previousUrl), 1000)
        }
      } else if (ndiLastFrameAt && Date.now() - ndiLastFrameAt > 5000) {
        img.removeAttribute('src')
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
  nowSourceEl.textContent = String(display.on_air_source_name || '').trim().toUpperCase() || '---'
  nextSourceEl.textContent = String(display.next_source_name || '').trim().toUpperCase() || '---'
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
    nowSourceEl.textContent = errorText(error)
    nextSourceEl.textContent = '---'
    renderPreview({ preview_mode: 'placeholder', preview_source_name: 'Preview unavailable' })
    renderMicTiles([])
  }

  refreshHandle = window.setInterval(() => {
    fetchState().catch((error) => {
      nowSourceEl.textContent = errorText(error)
    })
  }, DISPLAY_STATE_REFRESH_MS)
}

window.addEventListener('beforeunload', () => {
  if (refreshHandle) window.clearInterval(refreshHandle)
  if (clockHandle) window.clearInterval(clockHandle)
  stopNdiPreview()
})

start()
