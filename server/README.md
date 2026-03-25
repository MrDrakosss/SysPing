# Central Messenger Server

Ez a dokumentáció a központi Linux szerver telepítését, konfigurálását és automatikus indítását írja le.

A szerver feladata:
- a kliensek WebSocket kapcsolatait kezelni,
- nyilvántartani az ismert gépeket,
- online/offline státuszt követni,
- az üzeneteket MySQL adatbázisban tárolni,
- az offline gépeknek szánt üzeneteket sorban tartani,
- az admin kliens számára API-t biztosítani.

## Követelmények

- Linux szerver
- Python 3.11 vagy újabb
- MySQL 8 vagy MariaDB
- systemd
- hálózati elérés a választott szerverporton, például `8080`

## Ajánlott szerverstruktúra

```text
server/
├─ README.md
├─ main.py
├─ db.py
├─ models.py
├─ schemas.py
└─ .env
```

## Függőségek

A szerverhez ajánlott `requirements-server.txt` tartalma:

```txt
fastapi
uvicorn[standard]
sqlalchemy
pymysql
pydantic
python-dotenv
```

Telepítés virtuális környezetben:

```bash
cd /opt/central_messenger
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-server.txt
```

Ha kézzel telepíted a modulokat:

```bash
pip install fastapi "uvicorn[standard]" sqlalchemy pymysql pydantic python-dotenv
```

## Linux rendszercsomagok telepítése

Ubuntu vagy Debian alapú rendszeren:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server
```

MariaDB használata esetén:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mariadb-server
```

## Projektmappa létrehozása

```bash
sudo mkdir -p /opt/central_messenger
sudo chown $USER:$USER /opt/central_messenger
cd /opt/central_messenger
```

Git használata esetén:

```bash
git clone https://github.com/SAJAT_FELHASZNALO/central_messenger.git /opt/central_messenger
cd /opt/central_messenger
```

## MySQL adatbázis létrehozása

Jelentkezz be MySQL-be:

```bash
sudo mysql -u root -p
```

Majd hozd létre az adatbázist és a felhasználót:

```sql
CREATE DATABASE messenger_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'messenger_user'@'localhost' IDENTIFIED BY 'EROS_JELSZO';
GRANT ALL PRIVILEGES ON messenger_db.* TO 'messenger_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## Környezeti változók

Hozz létre egy `server/.env` fájlt:

```env
DATABASE_URL=mysql+pymysql://messenger_user:EROS_JELSZO@127.0.0.1/messenger_db?charset=utf8mb4
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
```

## Kézi indítás fejlesztéshez

```bash
cd /opt/central_messenger/server
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## Kézi indítás élesebb futtatáshoz

```bash
cd /opt/central_messenger/server
source ../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Automatikus indulás Linuxon systemd-vel

Hozz létre egy service fájlt:

```bash
sudo nano /etc/systemd/system/central-messenger.service
```

A fájl tartalma:

```ini
[Unit]
Description=Central Messenger Server
After=network.target mysql.service mariadb.service
Wants=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/central_messenger/server
Environment="PATH=/opt/central_messenger/.venv/bin"
ExecStart=/opt/central_messenger/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

A service aktiválása és kezelése:

```bash
sudo systemctl daemon-reload
sudo systemctl enable central-messenger.service
sudo systemctl start central-messenger.service
sudo systemctl restart central-messenger.service
sudo systemctl status central-messenger.service
journalctl -u central-messenger.service -f
```

## Tűzfal beállítása

Ha UFW fut a szerveren:

```bash
sudo ufw allow 8080/tcp
sudo ufw reload
sudo ufw status
```

## Opcionális Nginx reverse proxy

Nginx telepítése:

```bash
sudo apt install -y nginx
```

Konfiguráció létrehozása:

```bash
sudo nano /etc/nginx/sites-available/central-messenger
```

Példa tartalom:

```nginx
server {
    listen 80;
    server_name messenger.example.local;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Bekapcsolás:

```bash
sudo ln -s /etc/nginx/sites-available/central-messenger /etc/nginx/sites-enabled/central-messenger
sudo nginx -t
sudo systemctl restart nginx
```

## Gyors ellenőrzések

A szerver indulásának ellenőrzése:

```bash
sudo systemctl status central-messenger.service
journalctl -u central-messenger.service -f
```

FastAPI docs elérésének ellenőrzése:

```bash
curl http://127.0.0.1:8080/docs
```

vagy távolról:

```bash
curl http://SERVER_IP:8080/docs
```

## Mentés és visszaállítás

Mentés:

```bash
mysqldump -u messenger_user -p messenger_db > messenger_backup.sql
```

Visszaállítás:

```bash
mysql -u messenger_user -p messenger_db < messenger_backup.sql
```

## Frissítés

```bash
cd /opt/central_messenger
git pull
source .venv/bin/activate
pip install -r requirements-server.txt
sudo systemctl restart central-messenger.service
```

## Megjegyzések

- Éles környezetben ajánlott HTTPS / WSS használata.
- Érdemes később klienshitelesítést vagy tokenes védelmet beépíteni.
- A rendszer belső hálózatra készült, de reverse proxyval és TLS-sel biztonságosabbá tehető.
