let runtimeInstanceId = ''

async function checkRuntimeGeneration() {
  try {
    const response = await fetch('/api/runtime', { cache: 'no-store' })
    if (!response.ok) return
    const payload = await response.json()
    const nextInstanceId = String(payload.instance_id || '')
    if (!nextInstanceId) return
    if (runtimeInstanceId && runtimeInstanceId !== nextInstanceId) {
      window.location.reload()
      return
    }
    runtimeInstanceId = nextInstanceId
  } catch (_) {}
}

checkRuntimeGeneration()
window.setInterval(checkRuntimeGeneration, 2000)
