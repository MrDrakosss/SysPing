# SysPing Client

This document describes the SysPing Windows receiver client, its structure, configuration model, caching behavior, and packaging approach.

---

## Overview

The SysPing receiver client is a Windows desktop application that:

- runs in the background
- connects to the server by WebSocket
- receives messages in real time
- stores recent history locally
- shows message notifications
- supports important message alerts
- integrates with the system tray
- is intended to be deployed through a proper Windows installer

---

## Current Client Structure

```text
client/
├─ README.md
├─ receiver_client.py
├─ common.py
├─ installer/
│  ├─ README.md
│  └─ SysPing.iss
└─ receiver_app/
   ├─ __init__.py
   ├─ app.py
   ├─ config.py
   ├─ config_store.py
   ├─ cache_store.py
   ├─ models.py
   ├─ styles.py
   ├─ utils.py
   ├─ websocket_client.py
   ├─ tray.py
   ├─ dialogs.py
   ├─ chat_renderer.py
   ├─ single_instance.py
   ├─ autostart.py
   └─ main_window.py
```

---

## Main Components

### `receiver_client.py`
Entry point for the packaged application.

### `receiver_app/app.py`
Application startup, single-instance logic, Qt app initialization.

### `receiver_app/main_window.py`
Main chat UI and tray-driven receiver behavior.

### `receiver_app/websocket_client.py`
Background WebSocket thread for live message delivery and read acknowledgements.

### `receiver_app/chat_renderer.py`
HTML rendering for the chat message bubbles.

### `receiver_app/styles.py`
Qt stylesheet and dark-mode detection.

### `receiver_app/config_store.py`
XML-based configuration loading from machine-level storage.

### `receiver_app/cache_store.py`
Local JSON cache handling for message history optimization.

### `receiver_app/single_instance.py`
Prevents multiple client instances from running at the same time.

### `receiver_app/dialogs.py`
Important alert dialog logic.

### `receiver_app/tray.py`
System tray icon, menu, and unread-state handling.

---

## Configuration Storage

The packaged client is designed to use machine-level storage.

### Application files
```text
C:\Program Files\SysPing\
```

### Shared machine config and cache
```text
C:\ProgramData\SysPing\config.xml
C:\ProgramData\SysPing\cache.json
```

This avoids hardcoded server URLs inside the executable and allows central deployment with machine-specific or environment-specific settings.

---

## Configuration File Example

```xml
<?xml version="1.0" encoding="utf-8"?>
<SysPingConfig>
  <Server>
    <HttpUrl>http://127.0.0.1:8080</HttpUrl>
    <WsUrl>ws://127.0.0.1:8080/ws/client</WsUrl>
  </Server>
  <Client>
    <MachineName></MachineName>
    <AutoStart>true</AutoStart>
    <StartMinimized>true</StartMinimized>
  </Client>
</SysPingConfig>
```

### Notes
- If `MachineName` is empty, the client uses the local hostname.
- `HttpUrl` is used for REST calls such as branding and history.
- `WsUrl` is used for the live WebSocket connection.
- `AutoStart` is meant to be controlled by the installer and deployment policy.
- `StartMinimized` controls whether the window opens immediately or stays in the tray.

---

## Message Cache Behavior

To reduce unnecessary history reloads:
- the client stores recent messages locally
- the client remembers the latest known message ID
- on startup it first loads the local cache
- then it requests only newer messages from the server

Recommended server support:

```text
GET /client/messages/{machine_name}?after_id=123&limit=50
```

This makes startup faster and reduces repeated transfer of already known messages.

---

## Notifications

The receiver client supports:
- standard notification for normal messages
- highlighted alert dialog for important messages
- repeated reminders for unread important messages
- unread indicator in the tray icon

---

## Single Instance Protection

The client should run only once per machine session.

This is handled through a named mutex in:
- `receiver_app/single_instance.py`

If a second copy is started, the user is informed that the application is already running.

---

## Autostart Behavior

The recommended production setup is:
- configure autostart through the installer
- write machine-level autostart to:
  `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`

This ensures the client starts for all users on the machine after login.

---

## Development Run

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python client\receiver_client.py
```

---

## Packaging

The client is intended to be distributed as:
1. a PyInstaller-built executable
2. an Inno Setup installer

See:

```text
client/installer/README.md
```

for the exact build steps.

---

## Deployment Notes

The installer supports:
- interactive configuration through a wizard
- silent install with server URL parameters
- machine-level autostart
- uninstall cleanup of cache, config, and registry autostart entry

This makes it suitable for:
- manual installation
- Intune
- PDQ Deploy
- software deployment scripts
- domain rollout scenarios

---

## Troubleshooting

### Client starts more than once
Check single-instance protection and verify only one packaged executable is being launched.

### Client does not receive live messages
Check:
- WebSocket server URL
- firewall rules
- reverse proxy WebSocket forwarding
- server logs

### Client only receives messages after restart
Check:
- runtime online client registry on the server
- WebSocket path correctness
- reverse proxy WebSocket config
- live delivery path vs. queued delivery path

### UI is slow at startup
Use:
- local cache
- delayed background loading
- smaller initial history request

---

## Recommended Next Steps

- keep the client modular
- keep server URL out of the executable
- prefer installer-driven deployment
- use local cache with `after_id` sync
- use machine-level autostart through the installer
