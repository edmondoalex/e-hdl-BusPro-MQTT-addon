"""Isolated real Hub UI + eFace UI, synthetic HA only. Never connects to hardware.

python scripts/preview_mqtt_composite.py
http://127.0.0.1:8138/hub/index.html#mqtt
http://127.0.0.1:8138/eface/
"""
from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EFACE = ROOT.parent/'e-Face X4'/'e_face_x4'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EFACE))
directory = Path(tempfile.mkdtemp(prefix='mqtt-composite-preview-'))
os.environ['BUSPRO_STATE'] = str(directory/'state.json')
os.environ['ECONTROL_ORGANIZATION'] = str(directory/'organization.json')
os.environ['EFACE_ROUTINES_DB'] = str(directory/'routines.sqlite3')
os.environ.pop('SUPERVISOR_TOKEN', None)

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from e_hdl_buspro_mqtt.app.main import create_app
from e_hdl_buspro_mqtt.app.mqtt_manager import MqttCatalog
from app.connectors.buspro import normalize_snapshot
from app import routines

hub = create_app()
manager = hub.state.mqtt_manager
manager.devices = [{'id':'preview-motion', 'name':'Motion Cantina · DEMO', 'manufacturer':'Aqara', 'model':'Dati simulati'}]
rows = [('occupancy','binary_sensor','Occupazione',None,'off',{'device_class':'occupancy'}),
        ('illuminance','sensor','Illuminamento',None,'7',{'unit_of_measurement':'lx','device_class':'illuminance'}),
        ('battery','sensor','Batteria','diagnostic','100',{'unit_of_measurement':'%','device_class':'battery'}),
        ('temperature','sensor','Temperatura','diagnostic','23',{'unit_of_measurement':'°C','device_class':'temperature'}),
        ('interval','number','Detection interval','config','30',{'unit_of_measurement':'s','min':1,'max':600,'step':1}),
        ('sensitivity','select','Motion sensitivity','config','medium',{'options':['low','medium','high']}),
        ('indicator','switch','Trigger indicator','config','on',{})]
registry=[]
for key,domain,name,category,state,attrs in rows:
    eid=domain+'.preview_'+key
    registry.append({'id':key,'platform':'mqtt','entity_id':eid,'device_id':'preview-motion','entity_category':category,'name':name})
    manager.states[eid]={'entity_id':eid,'state':state,'attributes':attrs}
manager.store.sync_mqtt(registry,manager.states)
manager.last_sync=1
manager.connected=True
commands=[]

async def simulated_rest(method,path,data=None):
    if method=='GET' and path.startswith('/api/states/'):
        return manager.states[path.rsplit('/',1)[-1]]
    if method=='POST' and path.startswith('/api/services/'):
        commands.append({'path':path,'data':data})
        row=manager.states[data['entity_id']]
        row['state']=str(data.get('value',data.get('option','on' if path.endswith('/turn_on') else 'off')))
        return []
    return {}
manager.rest=simulated_rest
async def simulated_sync():return None
manager.sync=simulated_sync
client=TestClient(hub,base_url='http://testserver:8125')  # No context manager: no background/startup connections.
client.get('/api/organization')
app=FastAPI()

def catalog():
    response=client.get('/api/user/snapshot')
    return normalize_snapshot(response.json())['devices']

@app.get('/eface/api/bootstrap')
def bootstrap():
    devices=catalog()
    return {'version':'PREVIEW','dashboard':{'home':{'name':'Anteprima isolata'},'devices':devices,'rooms':[], 'widgets':[]},'providers':[]}

@app.get('/eface/api/user/routines/catalog')
def routine_catalog():return {'devices':catalog(),'filters':{'block_sensitive_names':False,'hide_readonly_actions':True}}

@app.get('/eface/api/user/routines')
def listing():return {'items':routines.list_routines()}

@app.post('/eface/api/user/routines/validate')
def validate(payload:dict):return routines.validate(payload.get('spec',{}),catalog())

@app.post('/eface/api/user/routines')
def save(payload:dict):
    review=routines.validate(payload.get('spec',{}),catalog())
    if review['errors']:raise HTTPException(400,review['errors'])
    return routines.save('preview','preview',None,review['spec'],False,None)

@app.post('/eface/api/devices/{device_id}/command')
async def command(device_id:str,payload:dict):
    action={'set_value':'level','select_option':'mode'}.get(payload['action'],payload['action'])
    return await manager.command_entity(device_id.removeprefix('mqtt:'),{'action':action,'value':payload.get('value')})

@app.get('/eface/api/icons/mdi/{name}')
def icon(name:str):
    response=client.get('/api/icons/mdi/'+name)
    return Response(response.content,status_code=response.status_code,media_type=response.headers.get('content-type'))

@app.get('/eface/api/{rest:path}')
def empty(rest:str):return {'items':[],'ids':[]}

@app.get('/preview/commands')
def calls():return commands

@app.post('/preview/reload-store')
def reload_store():
    # Only this isolated harness exposes a disk reload; no production route.
    manager.store = MqttCatalog(manager.store.path)
    return {'ok': True}

@app.get('/eface/')
def eface():return FileResponse(EFACE/'app/static/index.html')

@app.get('/eface/tools')
def tools():
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="assets/tools.css"><link rel="stylesheet" href="assets/routine-tools.css"></head><body><main class="tools-shell"><h1>Routine · anteprima isolata</h1><section id="tools-user-section"><div class="tools-grid"></div></section><section id="admin-tools"><div class="tools-grid"></div></section></main><script src="assets/routine-tools.js"></script></body></html>''')

app.mount('/eface/assets',StaticFiles(directory=EFACE/'app/static/assets'))
app.mount('/hub',hub)
if __name__=='__main__':
    print('ISOLATO: http://127.0.0.1:8138/hub/index.html#mqtt | /eface/ | /eface/tools',flush=True)
    uvicorn.run(app,host='127.0.0.1',port=8138,lifespan='off',access_log=False)
