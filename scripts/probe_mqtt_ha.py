"""Read-only capability probe. Starts and cancels empty HA forms; no submission."""
import asyncio
import json
import os
import urllib.request
from app.knx_manager import HomeAssistantWebSocket

TOKEN = os.environ['SUPERVISOR_TOKEN']


def request(method, path, data=None):
    req = urllib.request.Request('http://supervisor/core'+path, method=method,
        headers={'Authorization': 'Bearer '+TOKEN, 'Content-Type': 'application/json'},
        data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def schema(fields):
    return [{k: schema(v) if k == 'schema' else v for k, v in field.items()
             if k in ('name', 'type', 'required', 'selector', 'schema')} for field in fields]


async def main():
    ws = HomeAssistantWebSocket(TOKEN)
    entries = await ws.command('config_entries/get', domain='mqtt')
    registry = await ws.command('config/entity_registry/list')
    devices = await ws.command('config/device_registry/list')
    print(json.dumps({'mqtt_entries': len(entries), 'mqtt_entities': sum(r.get('platform')=='mqtt' for r in registry),
                      'mqtt_devices': sum(any(e['entry_id'] in r.get('config_entries', []) for e in entries) for r in devices),
                      'subentries_type': type(entries[0].get('subentries')).__name__ if entries else None}))
    if not entries: return
    eid = entries[0]['entry_id']
    for group, payload in [('', {'handler':'mqtt','entry_id':eid}),('options/',{'handler':eid}),('subentries/',{'handler':[eid,'device']})]:
        path='/api/config/config_entries/'+group+'flow'
        flow=request('POST',path,payload)
        try:
            print(json.dumps({'kind': group or 'connection', 'type':flow.get('type'), 'step':flow.get('step_id'), 'schema':schema(flow.get('data_schema',[]))}))
        finally:
            if flow.get('flow_id'): request('DELETE',path+'/'+flow['flow_id'])


asyncio.run(main())
