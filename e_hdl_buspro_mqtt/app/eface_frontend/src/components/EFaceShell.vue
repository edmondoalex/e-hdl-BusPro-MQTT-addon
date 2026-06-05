<template>
  <div class="eface-shell">
    <div class="ambient" :style="ambientStyle"></div>

    <header class="topbar glass">
      <div class="brand">
        <div class="mark">EF</div>
        <div>
          <h1>e-Face</h1>
          <p>{{ activeRoomName }} · {{ activeCategoryLabel }}</p>
        </div>
      </div>

      <div class="top-status">
        <div class="chip" :class="{ ok: online }">
          <span class="dot"></span>
          <span>{{ online ? 'online' : 'offline' }}</span>
        </div>
        <div class="chip">v{{ meta.version || '?' }}</div>
        <button class="icon-btn" type="button" title="Aggiorna" @click="refresh">
          <span class="mask" :style="mask('refresh')"></span>
        </button>
      </div>
    </header>

    <main class="console">
      <aside class="rail glass" aria-label="Categorie">
        <button
          v-for="cat in categories"
          :key="cat.id"
          class="rail-btn"
          :class="{ active: activeCategory === cat.id }"
          type="button"
          :title="cat.label"
          @click="activeCategory = cat.id"
        >
          <span class="mask" :style="mask(cat.icon)"></span>
          <small>{{ cat.short }}</small>
        </button>
      </aside>

      <section class="workspace">
        <section class="room-strip glass" v-if="rooms.length">
          <button
            v-for="room in rooms"
            :key="room"
            class="room-pill"
            :class="{ active: room === activeRoom }"
            type="button"
            @click="activeRoom = room"
          >
            <span class="mask" :style="mask(roomIcon(room))"></span>
            <strong>{{ room }}</strong>
            <small>{{ roomCount(room) }}</small>
          </button>
        </section>

        <section class="hero glass">
          <div>
            <p class="eyebrow">Control center</p>
            <h2>{{ activeRoomName }}</h2>
            <p class="muted">{{ heroSubtitle }}</p>
          </div>
          <div class="hero-metrics">
            <div><strong>{{ visibleDevices.length }}</strong><span>device</span></div>
            <div><strong>{{ onCount }}</strong><span>attivi</span></div>
            <div><strong>{{ rooms.length }}</strong><span>stanze</span></div>
          </div>
        </section>

        <section v-if="visibleDevices.length" class="device-grid">
          <article
            v-for="device in visibleDevices"
            :key="device.key"
            class="device-card glass"
            :class="{ active: isActive(device), dimmable: device.dimmable }"
            @click="toggleDevice(device)"
          >
            <div class="device-top">
              <button class="device-icon" type="button" :aria-pressed="isActive(device)" @click.stop="toggleDevice(device)">
                <span class="mask" :style="mask(device.iconName)"></span>
              </button>
              <div class="state">{{ stateLabel(device) }}</div>
            </div>
            <div class="device-text">
              <h3>{{ device.name }}</h3>
              <p>{{ device.meta }}</p>
            </div>
            <input
              v-if="device.kind === 'light' && device.dimmable"
              class="slider"
              type="range"
              min="1"
              max="255"
              :value="device.brightness || 180"
              @click.stop
              @change.stop="setBrightness(device, $event.target.value)"
            />
            <div v-if="device.kind === 'cover'" class="cover-actions">
              <button type="button" @click.stop="coverCmd(device, 'OPEN')">Su</button>
              <button type="button" @click.stop="coverCmd(device, 'STOP')">Stop</button>
              <button type="button" @click.stop="coverCmd(device, 'CLOSE')">Giu</button>
            </div>
          </article>
        </section>

        <section v-else class="empty glass">
          <span class="mask" :style="mask('shape')"></span>
          <h3>Nessun dispositivo</h3>
          <p>Questa categoria non ha dispositivi nella stanza selezionata.</p>
        </section>
      </section>

      <aside class="side glass">
        <h3>Impianto</h3>
        <div class="system-list">
          <div><span>Luci</span><strong>{{ stats.lights }}</strong></div>
          <div><span>Cover</span><strong>{{ stats.covers }}</strong></div>
          <div><span>Extra</span><strong>{{ stats.extra }}</strong></div>
          <div><span>Lock</span><strong>{{ stats.locks }}</strong></div>
        </div>
        <div class="quick-links">
          <a href="/home2">Home2</a>
          <a href="/lights">Luci</a>
          <a href="/covers">Cover</a>
          <a href="/extra">Extra</a>
        </div>
        <p class="muted small">{{ lastRefreshLabel }}</p>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getJson, mdiUrl, postJson } from '../api'

const meta = ref({})
const snapshot = ref({})
const online = ref(false)
const activeCategory = ref('lights')
const activeRoom = ref('')
const lastRefresh = ref(null)
let timer = null

const categories = [
  { id: 'lights', label: 'Luci', short: 'Luci', icon: 'lightbulb-group' },
  { id: 'covers', label: 'Cover', short: 'Cover', icon: 'window-shutter' },
  { id: 'locks', label: 'Sicurezza', short: 'Lock', icon: 'lock-smart' },
  { id: 'extra', label: 'Extra', short: 'Extra', icon: 'shape' }
]

const activeCategoryLabel = computed(() => categories.find(c => c.id === activeCategory.value)?.label || 'e-Face')

const devices = computed(() => {
  const list = Array.isArray(snapshot.value.devices) ? snapshot.value.devices : []
  return list.map(normalizeDevice).filter(Boolean)
})

const rooms = computed(() => {
  const seen = new Set()
  devices.value.forEach(d => seen.add(d.group || 'Generale'))
  return Array.from(seen).sort((a, b) => a.localeCompare(b, 'it', { sensitivity: 'base' }))
})

const activeRoomName = computed(() => activeRoom.value || rooms.value[0] || 'Casa')

const visibleDevices = computed(() => {
  const room = activeRoomName.value
  return devices.value
    .filter(d => (d.group || 'Generale') === room)
    .filter(d => categoryFor(d) === activeCategory.value)
})

const onCount = computed(() => visibleDevices.value.filter(isActive).length)

const stats = computed(() => ({
  lights: devices.value.filter(d => d.kind === 'light').length,
  covers: devices.value.filter(d => d.kind === 'cover').length,
  locks: devices.value.filter(d => categoryFor(d) === 'locks').length,
  extra: devices.value.filter(d => categoryFor(d) === 'extra').length
}))

const heroSubtitle = computed(() => {
  if (activeCategory.value === 'lights') return `${onCount.value} luci accese in questa stanza`
  if (activeCategory.value === 'covers') return 'Controllo tapparelle, tende e aperture'
  if (activeCategory.value === 'locks') return 'Serrature, cancelli e sicurezza'
  return 'Comandi rapidi, prese e servizi'
})

const ambientStyle = computed(() => {
  const room = activeRoomName.value.toLowerCase()
  const palette = room.includes('cucina') || room.includes('sala')
    ? ['rgba(225,80,65,.30)', 'rgba(231,190,98,.22)']
    : room.includes('esterno')
      ? ['rgba(48,120,165,.30)', 'rgba(74,175,119,.18)']
      : ['rgba(84,118,210,.26)', 'rgba(34,193,195,.18)']
  return {
    background: `radial-gradient(760px 460px at 20% 20%, ${palette[0]}, transparent 62%), radial-gradient(720px 520px at 84% 72%, ${palette[1]}, transparent 60%)`
  }
})

const lastRefreshLabel = computed(() => {
  if (!lastRefresh.value) return 'In attesa del primo aggiornamento'
  return `Aggiornato alle ${lastRefresh.value.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
})

function normalizeDevice(d) {
  if (!d || typeof d !== 'object') return null
  const type = String(d.type || d.domain || '').toLowerCase()
  const group = String(d.group || d.category || 'Generale').trim() || 'Generale'
  const origin = String(d.origin || '').toLowerCase()
  const entityId = String(d.entity_id || '').trim()
  const addr = entityId || `${d.subnet_id}.${d.device_id}.${d.channel}`
  const kind = type === 'cover' ? 'cover' : (type === 'lock' ? 'lock' : (type === 'switch' ? 'switch' : (type === 'light' ? 'light' : 'extra')))
  const state = stateFor(kind, d, addr)
  return {
    raw: d,
    key: `${kind}:${addr}`,
    addr,
    entityId,
    origin,
    kind,
    type,
    name: String(d.name || entityId || addr),
    group,
    category: String(d.category || ''),
    iconName: mdiName(d.icon, fallbackIcon(kind, d)),
    dimmable: !!d.dimmable,
    state: state.state,
    brightness: state.brightness,
    position: state.position,
    meta: entityId || addr
  }
}

function stateFor(kind, d, addr) {
  const states = snapshot.value.states || {}
  const covers = snapshot.value.cover_states || {}
  const ha = snapshot.value.ha_states || {}
  if (d.entity_id && ha[d.entity_id]) {
    const st = ha[d.entity_id] || {}
    return {
      state: String(st.state || '').toUpperCase(),
      brightness: Number(st.attributes?.brightness || 0),
      position: st.attributes?.current_position
    }
  }
  if (kind === 'cover') {
    const st = covers[addr] || {}
    return { state: String(st.state || '').toUpperCase(), position: st.position }
  }
  if (kind === 'light') {
    const st = states[addr] || {}
    return { state: String(st.state || '').toUpperCase(), brightness: Number(st.brightness || 0) }
  }
  return { state: '' }
}

function categoryFor(device) {
  if (device.kind === 'cover') return 'covers'
  if (device.kind === 'light') return 'lights'
  const cat = `${device.category} ${device.type} ${device.name}`.toLowerCase()
  if (device.kind === 'lock' || cat.includes('lock') || cat.includes('safe') || cat.includes('cancello') || cat.includes('portone')) return 'locks'
  return 'extra'
}

function isActive(device) {
  if (device.kind === 'cover') return !!device.state && device.state !== 'CLOSED'
  return device.state === 'ON' || device.state === 'OPEN' || device.state === 'UNLOCKED'
}

function stateLabel(device) {
  if (device.kind === 'cover') {
    if (device.position !== null && device.position !== undefined) return `${device.position}%`
    return device.state || 'cover'
  }
  if (device.kind === 'light' && device.dimmable && isActive(device)) {
    const pct = Math.round((Number(device.brightness || 0) / 255) * 100)
    return `${Math.max(1, pct)}%`
  }
  return isActive(device) ? 'ON' : 'OFF'
}

function mdiName(iconValue, fallback) {
  const raw = String(iconValue || '').trim()
  const match = /^mdi:([a-z0-9_-]+)$/i.exec(raw)
  return match ? match[1].toLowerCase() : fallback
}

function fallbackIcon(kind, device) {
  if (kind === 'light') return device.dimmable ? 'lightbulb-on' : 'lightbulb'
  if (kind === 'cover') return 'window-shutter'
  if (kind === 'lock') return 'lock-smart'
  if (kind === 'switch') return 'power'
  return 'shape'
}

function mask(icon) {
  return {
    WebkitMaskImage: `url("${mdiUrl(`mdi:${icon}`)}")`,
    maskImage: `url("${mdiUrl(`mdi:${icon}`)}")`
  }
}

function roomIcon(room) {
  const v = String(room || '').toLowerCase()
  if (v.includes('cucina')) return 'silverware-fork-knife'
  if (v.includes('sala')) return 'sofa'
  if (v.includes('bagno')) return 'shower'
  if (v.includes('garage')) return 'garage'
  if (v.includes('esterno')) return 'tree'
  if (v.includes('camera') || v.includes('cam ')) return 'bed'
  return 'home-variant'
}

function roomCount(room) {
  return devices.value.filter(d => (d.group || 'Generale') === room).length
}

async function toggleDevice(device) {
  try {
    if (device.kind === 'cover') {
      await coverCmd(device, isActive(device) ? 'CLOSE' : 'OPEN')
      return
    }
    const state = isActive(device) ? 'OFF' : 'ON'
    await sendOnOff(device, state, device.dimmable && state === 'ON' ? (device.brightness || 180) : null)
  } finally {
    setTimeout(refresh, 350)
  }
}

async function setBrightness(device, value) {
  await sendOnOff(device, 'ON', Number(value))
  setTimeout(refresh, 350)
}

async function sendOnOff(device, state, brightness = null) {
  const payload = { state }
  if (brightness !== null && brightness !== undefined) payload.brightness = Number(brightness)
  if (device.entityId) {
    const domain = device.entityId.split('.', 1)[0]
    if (domain === 'light') return postJson(`api/control/ha/light/${encodeURIComponent(device.entityId)}`, payload)
    if (domain === 'switch') return postJson(`api/control/ha/switch/${encodeURIComponent(device.entityId)}`, payload)
  }
  if (device.kind === 'light') {
    const [s, d, c] = device.addr.split('.')
    return postJson(`api/control/light/${s}/${d}/${c}`, payload)
  }
}

async function coverCmd(device, command) {
  try {
    if (device.entityId) {
      await postJson(`api/control/ha/cover/${encodeURIComponent(device.entityId)}`, { command })
    } else {
      const [s, d, c] = device.addr.split('.')
      await postJson(`api/control/cover/${s}/${d}/${c}`, { command })
    }
  } finally {
    setTimeout(refresh, 350)
  }
}

async function refresh() {
  try {
    const [nextMeta, nextSnapshot] = await Promise.all([
      getJson('api/meta').catch(() => ({})),
      getJson('api/user/snapshot')
    ])
    meta.value = nextMeta || {}
    snapshot.value = nextSnapshot || {}
    online.value = true
    lastRefresh.value = new Date()
    if (!activeRoom.value && rooms.value.length) activeRoom.value = rooms.value[0]
    if (activeRoom.value && !rooms.value.includes(activeRoom.value) && rooms.value.length) activeRoom.value = rooms.value[0]
  } catch (err) {
    online.value = false
    console.error('e-Face refresh failed', err)
  }
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 5000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>
