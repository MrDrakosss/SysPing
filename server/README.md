# SysPing Server

This document describes how to install, configure, run, and deploy the SysPing server on Linux.

---

## Overview

The SysPing server is the central component of the platform. It is responsible for:

- storing known devices
- tracking online / offline device state
- storing and delivering messages
- storing delivery and read timestamps
- exposing REST API endpoints
- handling WebSocket client sessions
- serving the web admin interface
- storing branding and admin-user settings

---

## Requirements

- Linux server
- Python 3.10+
- pip
- virtual environment support
- MySQL or MariaDB
- reverse proxy (Nginx or Apache) for production

---

## Directory Structure

Typical server structure inside the repository:

```text
server/
├─ api/
├─ services/
├─ webadmin/
├─ main.py
├─ db.py
├─ models.py
├─ schemas.py
├─ auth.py
├─ runtime_state.py
└─ .env
```

---

## Python Environment Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `pip` is missing:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
```

---

## Database Setup

Create a database and a dedicated user.

### MySQL / MariaDB example

```sql
CREATE DATABASE sysping CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'sysping_user'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON sysping.* TO 'sysping_user'@'localhost';
FLUSH PRIVILEGES;
```

---

## Environment File

Create or update `server/.env`:

```env
DATABASE_URL=mysql+pymysql://sysping_user:CHANGE_ME@127.0.0.1:3306/sysping?charset=utf8mb4
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
```

---

## Start the Server

From the repository root:

```bash
source .venv/bin/activate
cd server
uvicorn main:app --host 0.0.0.0 --port 8080
```

For development with auto-reload:

```bash
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## systemd Service

Create `/etc/systemd/system/sysping.service`:

```ini
[Unit]
Description=SysPing Server
After=network.target mysql.service mariadb.service

[Service]
Type=simple
User=YOUR_LINUX_USER
WorkingDirectory=/opt/SysPing/server
ExecStart=/opt/SysPing/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sysping
sudo systemctl start sysping
sudo systemctl status sysping
```

View logs:

```bash
journalctl -u sysping -f
```

---

## Reverse Proxy with Nginx

Example Nginx site config:

```nginx
server {
    listen 80;
    server_name sysping.example.local;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/sysping /etc/nginx/sites-enabled/sysping
sudo nginx -t
sudo systemctl reload nginx
```

---

## Reverse Proxy with Apache

Enable required modules:

```bash
sudo a2enmod proxy proxy_http proxy_wstunnel headers rewrite
sudo systemctl restart apache2
```

Example Apache virtual host:

```apache
<VirtualHost *:80>
    ServerName sysping.example.local

    ProxyPreserveHost On
    ProxyRequests Off

    ProxyPass /ws/ ws://127.0.0.1:8080/ws/
    ProxyPassReverse /ws/ ws://127.0.0.1:8080/ws/

    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    RequestHeader set X-Forwarded-Proto "http"
</VirtualHost>
```

Enable the site and reload:

```bash
sudo a2ensite sysping.conf
sudo apachectl configtest
sudo systemctl reload apache2
```

---

## Production Recommendations

- Use HTTPS in front of the reverse proxy
- Use WSS for WebSocket traffic in production
- Restrict database access to localhost or trusted subnets
- Use a strong password for the database user
- Back up the database regularly
- Keep the `.env` file out of public access
- Run the app behind a reverse proxy instead of exposing Uvicorn directly to the internet

---

## Basic Health Check

Open the root endpoint:

```text
http://SERVER:8080/
```

Expected response:

```json
{
  "name": "SysPing Server",
  "status": "ok"
}
```

---

## Web Admin

Default web admin path:

```text
http://SERVER:8080/webadmin/login
```

From there you can:
- manage devices
- send messages
- review delivery/read logs
- manage branding
- manage admin users

---

## Troubleshooting

### Database login failed
Check:
- `DATABASE_URL`
- MySQL user permissions
- MySQL service status

### Web admin shows template or route errors
Check:
- `server/webadmin/templates/`
- static files mount
- route imports in `server/main.py`

### WebSocket clients do not connect
Check:
- reverse proxy WebSocket headers
- firewall rules
- `/ws/client/{machine_name}` path
- server logs

### Changes in models are not reflected in the database
`Base.metadata.create_all()` does not update existing columns. Add missing columns manually or use a migration workflow.

---

## Useful Commands

```bash
sudo systemctl restart sysping
sudo systemctl status sysping
journalctl -u sysping -f
mysql -u sysping_user -p
```
