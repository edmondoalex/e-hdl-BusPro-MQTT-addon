"""MQTT administration through HA; never a second broker or a topic recorder."""
from __future__ import annotations

import asyncio
import base64
from collections import deque
from copy import deepcopy
from contextlib import asynccontextmanager
from hashlib import sha256
import json
import math
import time
import uuid
import urllib.request
from urllib.parse import urlsplit
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from .knx_manager import KnxCatalogStore, HomeAssistantWebSocket, _device_class, _capabilities


def topic(value, *, subscribe=False):
    if not isinstance(value, str) or not value or len(value.encode('utf-8')) > 1024 or '\x00' in value:
        raise ValueError('Topic non valido (massimo 1024 byte)')
    if subscribe:
        levels = value.split('/')
        if any(('+' in part and part != '+') or ('#' in part and (part != '#' or i != len(levels)-1)) for i, part in enumerate(levels)):
            raise ValueError('Wildcard MQTT non valida')
    elif '+' in value or '#' in value:
        raise ValueError('La pubblicazione non ammette wildcard')
    return value


def qos(value):
    if type(value) is not int or value not in (0, 1, 2):
        raise ValueError('QoS deve essere 0, 1 o 2')
    return value


class MqttCatalog(KnxCatalogStore):
    def __init__(self, path):
        super().__init__(path)
        self.data = super().load()

    def load(self):
        with self._lock:
            return deepcopy(self.data)

    def save(self, data):
        with self._lock:
            super().save(data)
            self.data = deepcopy(data)

    def sync_mqtt(self, registry, states):
        with self._lock:
            previous = self.data.get('devices', {})
            rows = {}
            for entry in registry:
                if entry.get('platform') != 'mqtt':
                    continue
                eid = entry.get('entity_id', '')
                rid = str(entry.get('id') or entry.get('unique_id') or eid)
                key = 'ha-' + sha256(rid.encode()).hexdigest()[:20]
                old = previous.get(key, {})
                state = states.get(eid, {})
                domain = eid.partition('.')[0]
                caps = _capabilities(domain, state)
                if domain == 'lock':
                    caps = ['lock', 'unlock']
                    if int(state.get('attributes', {}).get('supported_features') or 0) & 1:
                        caps.append('open')
                rows[key] = {'device_id': key, 'entity_id': eid, 'registry_id': rid,
                             'registry_device_id': entry.get('device_id'), 'config_entry_id': entry.get('config_entry_id'),
                             'config_subentry_id': entry.get('config_subentry_id'),
                             'entity_category': entry.get('entity_category'),
                             'icon': entry.get('icon') or entry.get('original_icon'),
                             'name': str(entry.get('name') or state.get('attributes', {}).get('friendly_name') or entry.get('original_name') or eid)[:160],
                             'domain': domain, 'device_class': _device_class(domain, state), 'capabilities': caps,
                             'disabled_by': entry.get('disabled_by'), 'orphaned': False,
                             'enabled': bool(old.get('enabled', False)), 'read_only': bool(old.get('read_only', True))}
            for key, old in previous.items():
                if key not in rows:
                    rows[key] = {**old, 'orphaned': True}
            # No periodic writes if the registry did not change; states remain RAM only.
            if rows != previous:
                self.save({**self.data, 'schema_version': 1, 'devices': rows, 'last_sync': int(time.time())})

    def rows(self, states, only_enabled=False, physical_id=None):
        result = []
        with self._lock:
            for item in self.data.get('devices', {}).values():
                if physical_id is not None and item.get('registry_device_id') != physical_id:
                    continue
                if only_enabled and not item.get('enabled'):
                    continue
                state = states.get(item['entity_id'], {})
                available = bool(state) and state.get('state') not in ('unknown', 'unavailable') and not item.get('orphaned') and not item.get('disabled_by')
                result.append({**deepcopy(item), 'source': 'mqtt', 'native_type': item['domain'],
                               'native_id': item['entity_id'], 'home_assistant_entity_id': item['entity_id'],
                               'available': available, 'stale': not available, 'state': deepcopy(state)})
        return result

    def catalog(self, states):
        rows = self.rows(states, only_enabled=True)
        with self._lock:
            presentations = deepcopy(self.data.get('presentations', {}))
        for row in rows:
            physical_id = row.get('registry_device_id')
            config = presentations.get(physical_id, {})
            if config.get('grouped'):
                row['presentation_group'] = {
                    'id': 'mqtt:device-' + sha256(physical_id.encode()).hexdigest()[:20],
                    'name': config.get('name') or physical_id,
                    'primary_id': 'mqtt:' + config.get('primary_id', ''),
                    'member_ids': ['mqtt:' + key for key in config.get('member_order', [])],
                }
        return rows

    def configure_device(self, physical_id, payload):
        """Atomically persist only an explicitly selected physical device's policies."""
        with self._lock:
            data = self.load()
            members = {key: row for key, row in data['devices'].items()
                       if row.get('registry_device_id') == physical_id and not row.get('orphaned')}
            changes = payload.get('entities')
            if not members or not isinstance(changes, dict) or set(changes) != set(members):
                raise ValueError('Il registro è cambiato: aggiorna il dispositivo prima di salvare')
            if type(payload.get('grouped')) is not bool:
                raise ValueError('Raggruppamento non valido')
            name = str(payload.get('name') or '').strip()
            if not name or len(name) > 160:
                raise ValueError('Nome dispositivo obbligatorio, massimo 160 caratteri')
            for key, policy in changes.items():
                if not isinstance(policy, dict) or type(policy.get('enabled')) is not bool or type(policy.get('commands')) is not bool:
                    raise ValueError('Permessi entità non validi')
                members[key]['enabled'] = policy['enabled']
                members[key]['read_only'] = not (policy['enabled'] and policy['commands'] and members[key].get('capabilities'))
            selected = [key for key, row in members.items() if row['enabled']]
            primary = payload.get('primary_id', '')
            if selected and primary not in selected:
                raise ValueError('Seleziona un’entità principale tra quelle esposte')
            order = payload.get('member_order', selected)
            if not isinstance(order, list) or any(not isinstance(key, str) for key in order) or len(order) != len(set(order)) or set(order) != set(selected):
                raise ValueError('Ordine entità non valido: deve contenere tutte e sole le entità selezionate')
            data.setdefault('presentations', {})[physical_id] = {
                'grouped': payload['grouped'], 'name': name, 'primary_id': primary if selected else '', 'member_order': order}
            self.save(data)
            return deepcopy(data['presentations'][physical_id])

    def organization_catalog(self):
        # Snapshot consumers need only these immutable metadata fields, not a
        # deep copy of thousands of HA registry records on every state update.
        with self._lock:
            return [{'device_id': row['device_id'], 'name': row['name'],
                     'device_class': row.get('device_class') or row['domain']}
                    for row in self.data.get('devices', {}).values() if not row.get('orphaned')]

    def update(self, device_id, *, enabled=None, read_only=None):
        with self._lock:
            row = self.data.get('devices', {}).get(device_id)
            if row is None:
                raise KeyError(device_id)
            if not (row.get('enabled') if enabled is None else enabled) or not row.get('capabilities'):
                read_only = True
            return super().update(device_id, enabled=enabled, read_only=read_only)


class MqttManager:
    def __init__(self, path, token, request):
        self.store = MqttCatalog(path)
        self.ws = HomeAssistantWebSocket(token)
        self.request = request
        self.states = {}
        self.devices = []
        self.entries = []
        self.flows = {}
        self.listeners = {}
        self.sync_lock = asyncio.Lock()
        self.last_sync = None
        self.error = ''
        self.connected = False
        self.on_state = None

    async def rest(self, method, path, data=None):
        return await asyncio.to_thread(self.request, method, path, payload=data, timeout_s=20)

    def device_detail(self, physical_id):
        device = next((row for row in self.devices if row['id'] == physical_id), None)
        if not device:
            raise KeyError('Dispositivo MQTT non trovato')
        rows = [row for row in self.store.rows(self.states, physical_id=physical_id) if not row.get('orphaned')]
        with self.store._lock:
            presentation = deepcopy(self.store.data.get('presentations', {}).get(physical_id, {}))
        return {'device': device, 'entities': rows, 'presentation': presentation}

    async def command_entity(self, entity_key, payload, *, administrative=False):
        """Admin is an independent permission; entity scope and live limits are shared."""
        with self.store._lock:
            row = deepcopy(self.store.data.get('devices', {}).get(entity_key))
        if not row or row.get('orphaned') or row.get('disabled_by'):
            raise ValueError('Entità MQTT non disponibile')
        if not administrative and (not row.get('enabled') or row.get('read_only')):
            raise ValueError('Comandi eFace non abilitati')
        state = await self.rest('GET', '/api/states/' + row['entity_id'])
        if not isinstance(state, dict) or state.get('state') in (None, 'unknown', 'unavailable'):
            raise ValueError('Stato attuale non disponibile')
        domain = row['domain']
        attrs = state.get('attributes') or {}
        action, value = payload.get('action'), payload.get('value')
        if action not in row.get('capabilities', []):
            raise ValueError('Comando non supportato dall’entità')
        service, data = '', {'entity_id': row['entity_id']}
        def number(minimum, maximum, step=None):
            if isinstance(value, bool):
                raise ValueError('Valore numerico non valido')
            try:
                result, lower, upper = float(value), float(minimum), float(maximum)
            except (ValueError, TypeError):
                raise ValueError('Limiti numerici non disponibili') from None
            if not all(math.isfinite(x) for x in (result, lower, upper)) or not lower <= result <= upper:
                raise ValueError('Valore fuori dai limiti del dispositivo')
            if step is not None:
                increment = float(step)
                if not math.isfinite(increment) or increment <= 0 or not math.isclose((result-lower)/increment, round((result-lower)/increment), abs_tol=1e-6):
                    raise ValueError('Valore non conforme al passo del dispositivo')
            return result
        if domain in ('light', 'switch', 'fan') and action in ('on', 'off'):
            service = 'turn_' + action
        elif domain == 'number' and action == 'level':
            service, data['value'] = 'set_value', number(attrs.get('min'), attrs.get('max'), attrs.get('step'))
        elif domain == 'select' and action == 'mode':
            if not isinstance(value, str) or value not in attrs.get('options', []):
                raise ValueError('Opzione non disponibile')
            service, data['option'] = 'select_option', value
        elif domain == 'button' and action == 'execute':
            service = 'press'
        elif domain == 'scene' and action == 'execute':
            service = 'turn_on'
        elif domain == 'light' and action == 'level':
            service, data['brightness_pct'] = 'turn_on', number(0, 100)
        elif domain == 'cover' and action in ('open', 'close', 'stop'):
            service = action + '_cover'
        elif domain == 'cover' and action == 'position':
            service, data['position'] = 'set_cover_position', number(0, 100, 1)
        elif domain == 'lock' and action in ('lock', 'unlock', 'open'):
            service = action
        elif domain == 'climate' and action == 'temperature':
            service, data['temperature'] = 'set_temperature', number(attrs.get('min_temp'), attrs.get('max_temp'))
        if not service:
            raise ValueError('Comando MQTT non supportato')
        await self.rest('POST', f'/api/services/{domain}/{service}', data)
        return {'ok': True, 'accepted': True, 'confirmed': False, 'source': 'mqtt'}

    @asynccontextmanager
    async def socket(self):
        import websockets
        async with websockets.connect(self.ws.url, open_timeout=8, close_timeout=2, max_size=4*1024*1024, max_queue=32) as ws:
            await asyncio.wait_for(ws.recv(), 8)
            await ws.send(json.dumps({'type': 'auth', 'access_token': self.ws.token}))
            auth = json.loads(await asyncio.wait_for(ws.recv(), 8))
            if auth.get('type') != 'auth_ok':
                raise RuntimeError('Autenticazione del servizio di integrazione non riuscita')
            yield ws

    async def sync(self):
        async with self.sync_lock:
            try:
                entries, registry, devices, states = await asyncio.gather(
                    self.ws.command('config_entries/get', domain='mqtt'),
                    self.ws.command('config/entity_registry/list'),
                    self.ws.command('config/device_registry/list'), self.ws.command('get_states'))
                ids = {row['entity_id'] for row in registry if row.get('platform') == 'mqtt'}
                self.states = {row['entity_id']: row for row in states if row.get('entity_id') in ids}
                self.store.sync_mqtt(registry, self.states)
                self.entries = [{k: row.get(k) for k in ('entry_id', 'title', 'state', 'supports_options', 'supports_reconfigure', 'supported_subentry_types', 'subentries')} for row in entries]
                for entry in self.entries:
                    entry['subentries'] = await self.ws.command('config_entries/subentries/list', entry_id=entry['entry_id'])
                entry_ids = {row['entry_id'] for row in entries}
                device_ids = {row.get('device_id') for row in registry if row.get('platform') == 'mqtt'}
                self.devices = [{k: row.get(k) for k in ('id', 'name', 'name_by_user', 'manufacturer', 'model', 'area_id', 'config_entries', 'config_entries_subentries')} for row in devices if row['id'] in device_ids or entry_ids.intersection(row.get('config_entries', []))]
                self.last_sync = time.time()
                self.error = ''
            except Exception:
                self.error = 'Sincronizzazione MQTT non disponibile; il catalogo precedente è conservato.'
                raise

    async def run(self):
        while True:
            try:
                await self.sync()
                async with self.socket() as ws:
                    await ws.send(json.dumps({'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'}))
                    ack = json.loads(await asyncio.wait_for(ws.recv(), 10))
                    if not ack.get('success'):
                        raise RuntimeError('Subscription non disponibile')
                    self.connected = True
                    deadline = time.monotonic() + 60
                    while True:
                        if time.monotonic() >= deadline:
                            await self.sync()
                            deadline = time.monotonic() + 60
                            for key, row in list(self.flows.items()):
                                if time.monotonic()-row['time'] > 1800:
                                    try: await self.cancel_flow(key)
                                    except Exception: pass
                        try:
                            msg = json.loads(await asyncio.wait_for(ws.recv(), min(10, max(.1, deadline-time.monotonic()))))
                        except asyncio.TimeoutError:
                            continue
                        data = msg.get('event', {}).get('data', {})
                        eid = data.get('entity_id')
                        if eid in self.states:
                            incoming = data.get('new_state') or {}
                            if not incoming or incoming.get('last_updated', '') >= self.states[eid].get('last_updated', ''):
                                previous = self.states[eid]
                                self.states[eid] = incoming
                                if self.on_state and incoming != previous:
                                    with self.store._lock:
                                        row = next((deepcopy(r) for r in self.store.data.get('devices', {}).values() if r['entity_id'] == eid), None)
                                    if row and row.get('enabled'):
                                        await self.on_state(row, incoming)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.connected = False
                self.states = {}
                self.error = 'Collegamento al servizio MQTT interrotto; nuovo tentativo automatico.'
                await asyncio.sleep(10)

    def entry(self, entry_id):
        if not any(row.get('entry_id') == entry_id for row in self.entries):
            raise ValueError('Integrazione MQTT non trovata: aggiorna il catalogo')

    async def start_flow(self, kind, entry_id='', subentry_id=''):
        if kind not in ('connection', 'options', 'device', 'setup'):
            raise ValueError('Operazione non supportata')
        if kind != 'setup':
            self.entry(entry_id)
        group = 'options/' if kind == 'options' else 'subentries/' if kind == 'device' else ''
        payload = {'handler': entry_id} if kind == 'options' else {'handler': [entry_id, 'device']} if kind == 'device' else {'handler': 'mqtt'}
        if kind == 'connection':
            payload['entry_id'] = entry_id
        if subentry_id:
            if kind != 'device':
                raise ValueError('Subentry non valida')
            entry = next(row for row in self.entries if row['entry_id'] == entry_id)
            if subentry_id not in {row.get('subentry_id') for row in entry.get('subentries') or []}:
                raise ValueError('Dispositivo MQTT non trovato')
            payload['subentry_id'] = subentry_id
        for key, row in list(self.flows.items()):
            if time.monotonic()-row['time'] > 1800:
                await self.cancel_flow(key)
        if len(self.flows) >= 8:
            raise ValueError('Chiudi le configurazioni già aperte')
        result = await self.rest('POST', '/api/config/config_entries/'+group+'flow', payload)
        fid = result.get('flow_id')
        if kind == 'setup' and result.get('type') == 'menu' and fid:
            # Configure only the HA client. Never offer broker installation here.
            result = await self.rest('POST', '/api/config/config_entries/flow/'+fid, {'next_step_id': 'broker'})
        if fid:
            self.flows[fid] = {'group': group, 'time': time.monotonic(), 'secrets': {}, 'uploads': [], 'file_fields': set()}
        return self.clean_flow(result)

    def clean_flow(self, result):
        result = deepcopy(result)
        flow = self.flows.get(result.get('flow_id'), {})
        def clean(fields, prefix=()):
            for field in fields or []:
                name = field.get('name', '')
                path = (*prefix, name)
                selector = field.get('selector', {})
                if 'file' in selector:
                    flow.setdefault('file_fields', set()).add('.'.join(path))
                if 'password' in name.lower() or selector.get('text', {}).get('type') == 'password':
                    value = field.pop('default', None)
                    value = field.get('description', {}).pop('suggested_value', value)
                    if value is not None:
                        flow.setdefault('secrets', {})[path] = value
                    field['secret_saved'] = bool(flow.get('secrets', {}).get(path))
                clean(field.get('schema'), path)
        clean(result.get('data_schema'))
        # HA create_entry can contain configuration. Never return stored credentials.
        if result.get('type') == 'create_entry':
            return {'type': 'create_entry', 'title': result.get('title'), 'applied': True}
        return {k: result[k] for k in ('type', 'flow_id', 'step_id', 'data_schema', 'errors', 'menu_options', 'reason', 'description_placeholders') if k in result}

    async def step_flow(self, fid, data):
        flow = self.flows.get(fid)
        if not flow or time.monotonic()-flow['time'] > 1800:
            raise ValueError('Configurazione scaduta: riaprila')
        if not isinstance(data, dict) or len(json.dumps(data)) > 65536:
            raise ValueError('Configurazione non valida')
        if data.get('next_step_id') in ('addon', 'install_addon', 'start_addon'):
            raise ValueError('Gestione broker esclusa: questa pagina configura solo il client MQTT')
        data = deepcopy(data)
        for path, value in flow['secrets'].items():
            target = data
            for part in path[:-1]:
                target = target.get(part, {}) if isinstance(target, dict) else {}
            if isinstance(target, dict) and target.get(path[-1]) == '':
                target[path[-1]] = value
        result = await self.rest('POST', '/api/config/config_entries/'+flow['group']+'flow/'+fid, data)
        flow['time'] = time.monotonic()
        cleaned = self.clean_flow(result)
        if result.get('type') in ('create_entry', 'abort'):
            await self.cleanup_uploads(flow)
            self.flows.pop(fid, None)
            try:
                await self.sync()
            except Exception:
                cleaned['verification_pending'] = True
        return cleaned

    async def cancel_flow(self, fid):
        flow = self.flows.pop(fid, None)
        if flow:
            try:
                await self.rest('DELETE', '/api/config/config_entries/'+flow['group']+'flow/'+fid)
            finally:
                await self.cleanup_uploads(flow)

    async def cleanup_uploads(self, flow):
        for file_id in flow.get('uploads', []):
            try: await self.rest('DELETE', '/api/file_upload', {'file_id': file_id})
            except Exception: pass  # HA already consumes files when applying TLS settings.

    async def upload(self, fid, payload):
        flow = self.flows.get(fid)
        if not flow or payload.get('field') not in flow.get('file_fields', set()) or time.monotonic()-flow['time'] > 1800:
            raise ValueError('Campo file non valido o configurazione scaduta')
        if len(flow['uploads']) >= 6:
            raise ValueError('Limite file per configurazione raggiunto')
        encoded = payload.get('content', '')
        if not isinstance(encoded, str) or len(encoded) > 180000:
            raise ValueError('Certificato massimo 128 KB')
        content = base64.b64decode(encoded, validate=True)
        if not content or len(content)>131072:
            raise ValueError('File non valido')
        # Fixed filename, no client-provided paths; binary DER and PEM both supported.
        boundary = uuid.uuid4().hex
        body = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="mqtt-certificate.pem"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+content+f'\r\n--{boundary}--\r\n'.encode()
        def send():
            req = urllib.request.Request('http://supervisor/core/api/file_upload', data=body,
                headers={'Authorization': 'Bearer '+self.ws.token, 'Content-Type':'multipart/form-data; boundary='+boundary}, method='POST')
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read())
        result = await asyncio.to_thread(send)
        flow['uploads'].append(result['file_id'])
        return {'file_id': result['file_id']}

    async def updates(self):
        config = await self.rest('GET', '/api/config')
        items = []
        for row in self.store.rows(self.states):
            if row['domain'] != 'update': continue
            attrs = row['state'].get('attributes', {})
            flags = int(attrs.get('supported_features') or 0)
            items.append({'device_id': row['device_id'], 'entity_id': row['entity_id'], 'name': row['name'],
                          'installed_version': attrs.get('installed_version'), 'latest_version': attrs.get('latest_version'),
                          'available': row['available'], 'update_available': row['state'].get('state') == 'on',
                          'can_install': bool(flags & 1), 'can_backup': bool(flags & 8), 'in_progress': attrs.get('in_progress')})
        return {'ha_version': config.get('version'), 'items': items,
                'client_note': 'Il client MQTT si aggiorna con il sistema, non separatamente. Qui aggiorni solo i firmware resi disponibili dai dispositivi. Broker escluso da questa pagina.'}

    async def install_update(self, device_id, payload):
        if payload.get('confirm') is not True:
            raise ValueError('Conferma aggiornamento richiesta')
        row = next((r for r in self.store.rows(self.states) if r['device_id'] == device_id), None)
        if not row or row['domain'] != 'update':
            raise ValueError('Entità aggiornamento MQTT non trovata')
        # Re-read HA before installing, not a possibly old catalog snapshot.
        state = await self.rest('GET', '/api/states/'+row['entity_id'])
        attrs = state.get('attributes', {})
        flags = int(attrs.get('supported_features') or 0)
        if state.get('state') != 'on' or not flags & 1 or attrs.get('in_progress'):
            raise ValueError('Aggiornamento non disponibile o già in corso')
        data = {'entity_id': row['entity_id']}
        if payload.get('backup'):
            if not flags & 8: raise ValueError('Backup non supportato da questo dispositivo')
            data['backup'] = True
        await self.ws.command('call_service', domain='update', service='install', service_data=data)
        return {'ok': True, 'message': 'Richiesta di aggiornamento inviata; verifica lo stato fino al completamento.'}

    async def publish(self, payload):
        target = topic(payload.get('topic'))
        quality = qos(payload.get('qos', 0))
        body = payload.get('payload', '')
        if not isinstance(body, str) or len(body.encode()) > 65536:
            raise ValueError('Payload massimo 64 KB')
        if payload.get('template'):
            body = await self.render_template(body)
            if len(body.encode()) > 65536:
                raise ValueError('Risultato template troppo grande')
        retain = payload.get('retain', False)
        if type(retain) is not bool:
            raise ValueError('Retain non valido')
        if retain and body == '' and payload.get('confirm_delete') is not True:
            raise ValueError('Conferma esplicita necessaria per cancellare un retained')
        await self.ws.command('call_service', domain='mqtt', service='publish', service_data={'topic': target, 'payload': body, 'qos': quality, 'retain': retain})
        return {'ok': True, 'message': 'Pubblicazione MQTT accettata; non è una conferma di esecuzione del dispositivo.'}

    async def render_template(self, template):
        def render():
            req = urllib.request.Request('http://supervisor/core/api/template', data=json.dumps({'template':template}).encode(),
                headers={'Authorization':'Bearer '+self.ws.token,'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req, timeout=20) as response:
                content = response.read(65537)
                if len(content)>65536: raise ValueError('Risultato template troppo grande')
                return content.decode('utf-8')
        return await asyncio.to_thread(render)

    async def listen(self, payload):
        target, quality = topic(payload.get('topic'), subscribe=True), qos(payload.get('qos', 0))
        for key, row in list(self.listeners.items()):
            if time.monotonic()-row['touch'] > 45:
                await self.stop_listener(key)
        if len(self.listeners) >= 4:
            raise ValueError('Massimo quattro sessioni di ascolto contemporanee')
        key = uuid.uuid4().hex
        ready = asyncio.get_running_loop().create_future()
        row = {'messages': deque(maxlen=200), 'sequence': 0, 'dropped': 0, 'touch': time.monotonic(), 'error': '', 'active': False}
        self.listeners[key] = row
        async def worker():
            try:
                async with self.socket() as ws:
                    await ws.send(json.dumps({'id': 1, 'type': 'mqtt/subscribe', 'topic': target, 'qos': quality}))
                    while time.monotonic()-row['touch'] < 45:
                        try:
                            message = json.loads(await asyncio.wait_for(ws.recv(), 10))
                        except asyncio.TimeoutError:
                            continue
                        if message.get('type') == 'result':
                            if not message.get('success'):
                                raise ValueError('Il servizio ha rifiutato la sottoscrizione MQTT')
                            row['active'] = True
                            if not ready.done(): ready.set_result(True)
                        elif message.get('type') == 'event':
                            event = message.get('event', {})
                            row['sequence'] += 1
                            if len(row['messages']) == 200: row['dropped'] += 1
                            content = str(event.get('payload', ''))
                            row['messages'].append({'id': row['sequence'], 'time': time.time(), 'topic': str(event.get('topic', ''))[:1024],
                                                    'payload': content[:4096], 'truncated': len(content)>4096, 'qos': event.get('qos'), 'retain': event.get('retain')})
            except asyncio.CancelledError:
                raise
            except Exception:
                row['error'] = 'Ascolto interrotto: verifica il collegamento e riavvia la sessione.'
                if not ready.done(): ready.set_exception(ValueError(row['error']))
            finally:
                row['active'] = False
                if not ready.done(): ready.set_exception(ValueError('Ascolto scaduto'))
        row['task'] = asyncio.create_task(worker())
        try:
            await asyncio.wait_for(ready, 15)
        except Exception:
            await self.stop_listener(key)
            raise
        return {'id': key}

    def messages(self, key, after=0):
        row = self.listeners.get(key)
        if not row:
            raise KeyError(key)
        row['touch'] = time.monotonic()
        return {'messages': [m for m in row['messages'] if m['id'] > after], 'cursor': row['sequence'], 'dropped': row['dropped'], 'active': row['active'], 'error': row['error']}

    async def stop_listener(self, key):
        row = self.listeners.pop(key, None)
        if row:
            row['task'].cancel()
            await asyncio.gather(row['task'], return_exceptions=True)

    async def close(self):
        for key in list(self.listeners):
            await self.stop_listener(key)
        for key in list(self.flows):
            try: await self.cancel_flow(key)
            except Exception: pass


def install_routes(api, manager, refresh_organization, other_devices, save_policies=None, admin_command=None):
    prefix = '/api/integrations/mqtt'
    app = api

    async def protect(request: Request, response: Response):
        response.headers['Cache-Control'] = 'no-store'
        if request.method != 'GET':
            origin = request.headers.get('origin')
            if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and urlsplit(origin).netloc != request.headers.get('host')):
                raise HTTPException(403, detail='Origine non consentita')
            if request.method == 'POST':
                if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
                    raise HTTPException(415, detail='Richiesto JSON')
                if len(await request.body()) > 200000:
                    raise HTTPException(413, detail='Richiesta troppo grande')

    api = APIRouter(dependencies=[Depends(protect)])

    async def guarded(fn, *args):
        try:
            return await fn(*args)
        except (ValueError, KeyError) as exc:
            raise HTTPException(400, detail=str(exc)) from None
        except Exception:
            # Upstream errors can echo secrets or payloads. Do not leak them.
            raise HTTPException(502, detail='Operazione MQTT non riuscita. Verifica connessione e configurazione.') from None

    @api.get(prefix)
    async def mqtt_overview():
        if manager.last_sync is None:
            await guarded(manager.sync)
            refresh_organization()
        rows = manager.store.rows(manager.states)
        duplicates = {}
        for item in other_devices():
            eid = item.get('home_assistant_entity_id')
            if eid and item.get('source') != 'mqtt':
                duplicates.setdefault(eid, []).append(item.get('source'))
        for row in rows:
            row['also_in'] = sorted(set(duplicates.get(row['entity_id'], [])))
        return {'entries': manager.entries, 'devices': manager.devices, 'entities': rows,
                'last_sync': manager.last_sync, 'realtime': manager.connected, 'error': manager.error,
                'counts': {'devices': len(manager.devices), 'entities': sum(not r.get('orphaned') for r in rows), 'exported': sum(r['enabled'] for r in rows)}}

    @api.get(prefix+'/client-status')
    async def mqtt_client_status():
        return {'configured': bool(manager.entries), 'loaded': any(e.get('state') == 'loaded' for e in manager.entries),
                'realtime': manager.connected, 'error': manager.error}

    @api.get(prefix+'/devices/{device_id}')
    async def mqtt_device(device_id: str):
        try:
            return manager.device_detail(device_id)
        except KeyError:
            raise HTTPException(404, detail='Dispositivo MQTT non trovato') from None

    @api.put(prefix+'/devices/{device_id}/presentation')
    async def mqtt_device_presentation(device_id: str, payload: dict):
        try:
            manager.device_detail(device_id)
            result = manager.store.configure_device(device_id, payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, detail=str(exc)) from None
        if save_policies:
            save_policies(payload['entities'])
        refresh_organization()
        return result

    @api.post(prefix+'/entities/{entity_key}/command')
    async def mqtt_admin_command(entity_key: str, payload: dict):
        async def execute():
            if admin_command:
                return await admin_command(entity_key, payload)
            return await manager.command_entity(entity_key, payload, administrative=True)
        return await guarded(execute)

    @api.post(prefix+'/sync')
    async def mqtt_sync():
        await guarded(manager.sync)
        refresh_organization()
        return {'ok': True}

    @api.post(prefix+'/flow')
    async def mqtt_flow(payload: dict):
        return await guarded(manager.start_flow, payload.get('kind'), payload.get('entry_id', ''), payload.get('subentry_id', ''))

    @api.post(prefix+'/flow/{fid}')
    async def mqtt_flow_step(fid: str, payload: dict):
        return await guarded(manager.step_flow, fid, payload)

    @api.delete(prefix+'/flow/{fid}')
    async def mqtt_flow_cancel(fid: str):
        await guarded(manager.cancel_flow, fid)
        return {'ok': True}

    @api.post(prefix+'/flow/{fid}/file')
    async def mqtt_file(fid: str, payload: dict):
        return await guarded(manager.upload, fid, payload)

    @api.get(prefix+'/updates')
    async def mqtt_updates():
        return await guarded(manager.updates)

    @api.post(prefix+'/updates/{device_id}')
    async def mqtt_update(device_id: str, payload: dict):
        return await guarded(manager.install_update, device_id, payload)

    @api.get(prefix+'/devices/{device_id}/debug')
    async def mqtt_debug(device_id: str):
        if not any(row['id'] == device_id for row in manager.devices):
            raise HTTPException(404, detail='Dispositivo MQTT non trovato')
        async def read():
            return await manager.ws.command('mqtt/device/debug_info', device_id=device_id)
        return await guarded(read)

    @api.post(prefix+'/publish')
    async def mqtt_publish(payload: dict):
        return await guarded(manager.publish, payload)

    @api.post(prefix+'/listen')
    async def mqtt_listen(payload: dict):
        return await guarded(manager.listen, payload)

    @api.get(prefix+'/listen/{key}')
    async def mqtt_messages(key: str, after: int = 0):
        try: return manager.messages(key, max(0, after))
        except KeyError: raise HTTPException(404, detail='Sessione terminata') from None

    @api.delete(prefix+'/listen/{key}')
    async def mqtt_stop(key: str):
        await manager.stop_listener(key)
        return {'ok': True}

    app.include_router(api)
