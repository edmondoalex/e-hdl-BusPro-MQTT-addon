export function apiUrl(path) {
  return new URL(path, window.location.href).toString()
}

export async function getJson(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    cache: 'no-store',
    ...options,
    headers: {
      ...(options.headers || {})
    }
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}

export async function postJson(path, payload = {}) {
  return getJson(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export function mdiUrl(iconValue, fallback = 'shape') {
  const raw = String(iconValue || '').trim()
  const match = /^mdi:([a-z0-9_-]+)$/i.exec(raw)
  const name = match ? match[1].toLowerCase() : fallback
  return apiUrl(`api/icons/mdi/${name}.svg`)
}
