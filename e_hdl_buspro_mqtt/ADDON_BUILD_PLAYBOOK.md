# Add-on Playbook (BusPro MQTT) – build + bugfix

Questo file riassume i passaggi fatti e i bug corretti per arrivare ad un add-on Home Assistant con Web UI funzionante sia via porta web sia via Ingress (barra laterale).

## Contesto
- Add-on locale in `\\192.168.3.24\addons\e_hdl_buspro_mqtt`
- Backend: FastAPI + Uvicorn
- MQTT: `paho-mqtt` v2
- UI: HTML/JS statico servito da FastAPI

## Sequenza di problemi incontrati e soluzioni

### 1) Add-on non visibile nello Store
**Sintomo**: non compare tra i Local add-ons.

**Cause e fix**
- Presenza di `repository.yaml` nella root: Supervisor interpreta la cartella come *repository* e cerca add-on solo in sottocartelle.
  - Fix: rimosso `repository.yaml`.
- Nome cartella diverso dallo `slug`.
  - Fix: rinominata la cartella a `e_hdl_buspro_mqtt` per combaciare con `slug: e_hdl_buspro_mqtt`.

### 2) Supervisor non legge `config.json`
**Sintomo**: log Supervisor: `Can't read json ... unexpected character: line 1 column 1`.

**Causa**: `config.json` salvato con UTF-8 BOM.

**Fix**: riscritto `config.json` in UTF-8 senza BOM.

### 3) Errore validazione `webui`
**Sintomo**: `does not match regular expression ... data['webui'] Got 'http://[HOST]:8124'`.

**Fix**: usare placeholder porta: `webui: "http://[HOST]:[PORT:8124]"`.

### 4) Pull immagine fallisce (404) invece di build locale
**Sintomo**: `pull access denied for local/... repository does not exist`.

**Causa**: campo `image` in `config.json` puntava a un’immagine inesistente.

**Fix**: rimosso `image` per forzare build locale dal `Dockerfile`.

### 5) Build fallisce per PEP 668 (`externally-managed-environment`)
**Sintomo**: in build output: `error: externally-managed-environment` durante `pip install --upgrade pip`.

**Fix**: installare dipendenze in virtualenv:
- `python3 -m venv /opt/venv`
- `pip install ...` dentro `/opt/venv`
- `run.sh` avvia `/opt/venv/bin/python -m app.main`

### 6) `run.sh` non eseguibile: shebang rotto
**Sintomo**: `/app/run.sh: line 1: ﻿#!/usr/bin/with-contenv: not found`.

**Causa**: BOM anche su `run.sh`.

**Fix**: riscritto `run.sh` senza BOM (UTF-8 no BOM).

### 7) Dockerfile invalido (continuazioni `\` sbagliate)
**Sintomo**: build “unknown error” / errori durante parsing ENV.

**Causa**: `ENV` con sequenze `\\` (backslash duplicati) e continuazioni errate.

**Fix**: riscritto `Dockerfile` con backslash singoli corretti.

### 8) Crash su shutdown: callback MQTT `on_disconnect` (paho-mqtt v2)
**Sintomo**: `TypeError: MqttClient._on_disconnect() ... but 6 were given`.

**Causa**: in paho-mqtt v2 la firma `on_disconnect` include `disconnect_flags`.

**Fix**: aggiornato `MqttClient._on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None)`.

### 9) Ingress/Sidebar 503
**Sintomo**: UI ok su porta web, ma `503 Service Unavailable` da barra laterale.

**Fix**
- Disabilitato `host_network`: con host network l’Ingress spesso non riesce a fare proxy correttamente.
- Bypass auth interna quando la richiesta arriva via Ingress (header ingress): Ingress è già autenticato da Home Assistant.

### 10) Ingress: `{"detail":"Not Found"}`
**Sintomo**: aprendo via sidebar o “Apri interfaccia web” appare JSON `Not Found`.

**Cause e fix**
- La UI chiamava `/api/...` assoluto: dietro Ingress questi path puntano a Home Assistant, non all’add-on.
  - Fix: in `index.html` usati path relativi `./api/...`.
- Proxy/Ingress può inoltrare richieste con prefisso base (es. `/local_<slug>/...`) senza strip.
  - Fix: middleware che riconosce base path da `X-Forwarded-Prefix` o `x-ingress-path` (e fallback su `/local_*`) e riscrive `scope['path']`.
- Aggiunta route fallback “SPA” per servire l’UI su path non previsti dietro proxy.

## Scelte pratiche che hanno aiutato
- Usare sempre UTF-8 *senza BOM* per `config.json` e script shell.
- Non impostare `image` nei local add-ons (lasciare build locale da Dockerfile).
- Per Alpine: installare Python packages in venv (`/opt/venv`) per evitare PEP 668.
- Per Ingress: evitare `host_network` e usare API paths relativi.

## Checklist per un nuovo add-on (riutilizzabile)
1) Cartella sotto `addons/` con nome uguale a `slug`.
2) `config.json` senza BOM, `webui` con `[PORT:...]`.
3) Niente `repository.yaml` nella root del singolo add-on.
4) Niente `image` se vuoi build locale.
5) Dockerfile con venv e `run.sh` senza BOM.
6) Se usi MQTT paho v2: firme callback compatibili.
7) Se vuoi sidebar: `ingress: true` + `panel_title/panel_icon`, API relative e gestione base-path.

## Riferimenti file nel progetto
- Config add-on: `config.json`
- Docker build/runtime: `Dockerfile`, `run.sh`
- Backend: `app/main.py`, `app/mqtt_client.py`, `app/settings.py`
- UI: `app/static/index.html`
- Log dei cambi: `WORKLOG.md`