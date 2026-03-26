# SysPing

SysPing is a centralized internal messaging system for Windows endpoints with a Linux-hosted backend, a web-based admin dashboard, and a receiver client that runs in the background on user machines.

The system is designed for internal IT communication scenarios where administrators need to send messages to known devices, handle offline delivery, track delivery and read status, and manage endpoint metadata from a central server.

---

## Features

### Server
- FastAPI-based backend
- MySQL / MariaDB database support
- Central device registry
- Online / offline device tracking
- Delivery queue for offline devices
- Delivery and read status tracking
- REST API for admin and client communication
- WebSocket-based real-time delivery
- Web admin dashboard
- Branding support
- Admin user management
- Message history and statistics

### Receiver Client
- Background-running Windows client
- System tray integration
- Automatic server connection
- Chat-like message interface
- Separate conversations by sender
- Unread message indicator
- Standard notification for normal messages
- Elevated alert dialog for important messages
- Repeated reminder for unread important messages
- Local configuration and cache support
- Installable package support

### Web Admin
- Login-protected dashboard
- Device search and metadata management
- Message sending to one or multiple devices
- Own sent-message view
- Full message log for superadmins
- Delivery and read timestamps
- Branding and settings management
- Responsive mobile-friendly UI

---

## Repository Layout

```text
SysPing/
├─ client/
│  ├─ README.md
│  ├─ receiver_client.py
│  ├─ common.py
│  ├─ installer/
│  │  ├─ README.md
│  │  └─ SysPing.iss
│  └─ receiver_app/
├─ server/
│  ├─ README.md
│  ├─ api/
│  ├─ services/
│  ├─ webadmin/
│  ├─ main.py
│  ├─ db.py
│  ├─ models.py
│  ├─ schemas.py
│  └─ .env
├─ README.md
└─ requirements.txt
```

---

## Technology Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- PyMySQL
- Uvicorn
- MySQL / MariaDB
- Jinja2
- WebSockets

### Client
- Python
- PySide6
- websocket-client
- PyInstaller
- Inno Setup

---

## Quick Start

### 1. Server
See [`server/README.md`](server/README.md) for:
- Linux installation
- Python environment setup
- MySQL configuration
- `.env` configuration
- systemd service setup
- Nginx reverse proxy
- Apache reverse proxy

### 2. Client
See [`client/README.md`](client/README.md) for:
- development setup
- configuration
- installable client structure
- cache and config storage
- autostart behavior
- packaging notes

### 3. Installer Build
See [`client/installer/README.md`](client/installer/README.md) for:
- PyInstaller build
- Inno Setup build
- silent install parameters
- Intune command example

---

## Current Architecture

- The **server** stores devices, admin users, branding settings, and all messages.
- The **receiver client** connects over WebSocket and receives real-time messages.
- If a target device is offline, the server stores the message and delivers it when the device reconnects.
- The **web admin** is the main operator interface for sending messages and reviewing message history.
- The **receiver client** stores local configuration and message cache for faster startup and lighter history synchronization.

---

## Production Notes

- Run the server behind a reverse proxy in production.
- Use HTTPS / WSS in real deployments.
- Store MySQL credentials in `server/.env`.
- Deploy the Windows client through the installer for proper configuration, autostart, and uninstall support.
- Use the silent installer parameters for centralized rollout tools such as Intune, PDQ Deploy, or GPO-based scripting.

---

## License

Add your preferred license here before production release.
