# SysPing Client Installer – Build Guide

This document covers the Windows build process for the SysPing receiver installer.

---

## Requirements

You need:

- Python 3.10+
- pip
- PyInstaller
- Inno Setup 6

---

## Create a Python Virtual Environment

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

---

## Install Required Python Packages

From the repository root:

```bash
pip install -r requirements.txt
```

If you want to install the minimum set manually:

```bash
pip install PySide6 websocket-client requests pyinstaller
```

---

## Build the Client EXE

```bash
pyinstaller --noconfirm --onefile --windowed --name SysPingReceiver client\receiver_client.py
```

Output:

```text
dist\SysPingReceiver.exe
```

---

## Install Inno Setup

Download and install Inno Setup 6 from:

```text
https://jrsoftware.org/isdl.php
```

Default compiler path:

```text
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

---

## Build the Installer

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "client\installer\SysPing.iss"
```

Output:

```text
client\installer\output\SysPingInstaller.exe
```

---

## Interactive Installation

The installer wizard allows you to configure:

- HTTP server URL
- WebSocket server URL
- machine-level autostart
- start minimized / tray startup

The installer writes these values to:

```text
C:\ProgramData\SysPing\config.xml
```

---

## Silent Installation

Example silent deployment:

```bash
SysPingInstaller.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART ^
/SERVERHTTP="http://192.168.1.10:8080" ^
/SERVERWS="ws://192.168.1.10:8080/ws/client" ^
/AUTOSTART=1 ^
/STARTMINIMIZED=1
```

### Parameters

| Parameter | Description |
|---|---|
| `/SERVERHTTP` | HTTP API base URL |
| `/SERVERWS` | WebSocket base URL |
| `/AUTOSTART` | `1` enables machine-level autostart |
| `/STARTMINIMIZED` | `1` starts the client in the tray / minimized mode |

---

## Intune Install Command

```powershell
Start-Process -FilePath ".\SysPingInstaller.exe" -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SERVERHTTP="http://192.168.1.10:8080" /SERVERWS="ws://192.168.1.10:8080/ws/client" /AUTOSTART=1 /STARTMINIMIZED=1' -Wait
```

---

## Full Build Flow

```bash
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name SysPingReceiver client\receiver_client.py
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "client\installer\SysPing.iss"
```

---

## Common Issues

### EXE not found
Build the executable first with PyInstaller.

### `pip` is not available
Install or bootstrap it:

```bash
python -m ensurepip --upgrade
```

### `ISCC.exe` not found
Check the local Inno Setup install path.

### PowerShell does not execute `ISCC.exe`
Use the call operator:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "client\installer\SysPing.iss"
```
