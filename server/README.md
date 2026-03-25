# Central Messenger Client

Ez a dokumentáció a Windowsos kliensalkalmazások telepítését, konfigurációját, buildelését és automatikus indulását írja le.

A kliensoldalon két alkalmazás van:
- `receiver_client.py` – végfelhasználói fogadó kliens
- `admin_client.py` – rendszergazdai kliens, amely küldeni és fogadni is tud

## Fő funkciók

### Receiver kliens
- a háttérben csatlakozik a szerverhez
- online státuszt küld
- fogadja az új üzeneteket
- gépenként külön chateket mutat
- fontos üzenetnél kiemelt figyelmeztetés jelenik meg
- olvasatlan fontos üzenetnél 10 percenként ismételt popup értesítés

### Admin kliens
- a szerverről ismert gépekből lehet választani
- keresőmezővel szűrhető a géplista
- küldés egy vagy több gépnek
- saját maga is fogad üzenetet
- gépekhez tulajdonos és megjegyzés rendelhető
- törölhető vagy inaktiválható az elavult gép

## Ajánlott fájlstruktúra

```text
client/
├─ README.md
├─ common.py
├─ admin_client.py
├─ receiver_client.py
└─ assets/
   └─ app.ico
```

## Kliens oldali függőségek

Ajánlott `requirements-client.txt`:

```txt
PySide6
websocket-client
requests
pyinstaller
```

Telepítés virtuális környezetbe:

### PowerShell

```powershell
cd C:\central_messenger
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-client.txt
```

Ha kézzel telepíted a modulokat:

```powershell
pip install PySide6 websocket-client requests pyinstaller
```

## Kliens konfiguráció

A `client/common.py` fájlban állítsd be a szerver címét:

```python
SERVER_HTTP = "http://192.168.1.10:8080"
SERVER_WS = "ws://192.168.1.10:8080/ws/client"
```

HTTPS / WSS esetén:

```python
SERVER_HTTP = "https://messenger.example.local"
SERVER_WS = "wss://messenger.example.local/ws/client"
```

## Futtatás fejlesztői módban

Receiver kliens:

```powershell
cd C:\central_messenger
.venv\Scripts\activate
python client\receiver_client.py
```

Admin kliens:

```powershell
cd C:\central_messenger
.venv\Scripts\activate
python client\admin_client.py
```

## EXE build

A felhasználóknak jellemzően EXE-t érdemes teríteni.

Receiver kliens build:

```powershell
pyinstaller --noconfirm --onefile --windowed client\receiver_client.py
```

Admin kliens build:

```powershell
pyinstaller --noconfirm --onefile --windowed client\admin_client.py
```

Ikonnal:

```powershell
pyinstaller --noconfirm --onefile --windowed --icon client\assets\app.ico client\receiver_client.py
pyinstaller --noconfirm --onefile --windowed --icon client\assets\app.ico client\admin_client.py
```

A buildelt fájlok a `dist\` mappába kerülnek.

## Automatikus indulás Windowson

A fogadó kliens tipikusan automatikusan induljon a Windows bejelentkezéskor.

### Egyszerű módszer: Startup mappa

Nyisd meg a Startup mappát:

```text
Win + R
shell:startup
```

Ezután hozz létre ide egy parancsikont a buildelt `receiver_client.exe` fájlhoz, például:

```text
C:\central_messenger\dist\receiver_client.exe
```

Így a fogadó kliens automatikusan elindul minden bejelentkezéskor.

### Stabilabb módszer: Feladatütemező

A Windows Task Scheduler használható, ha megbízhatóbb indítást szeretnél.

Általános beállítás:
- Trigger: bejelentkezéskor
- Action: a `receiver_client.exe` futtatása
- Szükség esetén: `Run with highest privileges`

## Linux kliens automatikus indulás példája

Ha később Linux kliensre is szükség lenne, grafikus környezetben készíthető autostart fájl.

Mappa létrehozása:

```bash
mkdir -p ~/.config/autostart
```

Autostart fájl:

```bash
nano ~/.config/autostart/central-receiver.desktop
```

Tartalom:

```ini
[Desktop Entry]
Type=Application
Name=Central Receiver
Exec=/opt/central_messenger/client/start_receiver.sh
X-GNOME-Autostart-enabled=true
```

Indító script:

```bash
nano /opt/central_messenger/client/start_receiver.sh
```

Tartalom:

```bash
#!/bin/bash
cd /opt/central_messenger/client
source ../.venv/bin/activate
python receiver_client.py
```

Futtathatóvá tétel:

```bash
chmod +x /opt/central_messenger/client/start_receiver.sh
```

## Kliensellenőrzés

Indítás után ellenőrizd:
- elindul-e a kliens,
- felcsatlakozik-e a szerverre,
- megjelenik-e online gépként az admin oldalon,
- fogad-e üzenetet,
- fontos üzenetnél megjelenik-e a popup,
- olvasatlan fontos üzenetnél ismétlődik-e az értesítés.

## Gyakori hibák

### Nem csatlakozik a kliens
Ellenőrizd:
- helyes-e a `SERVER_HTTP`,
- helyes-e a `SERVER_WS`,
- elérhető-e a szerver hálózaton,
- nyitva van-e a szerver portja,
- nincs-e tűzfal tiltás.

### Nem indul az EXE
Ellenőrizd:
- a build sikeres volt-e,
- a `dist` mappában létrejött-e a fájl,
- a vírusirtó nem blokkolja-e,
- kézzel elindítható-e.

### Nem indul automatikusan
Ellenőrizd:
- a Startup mappába tényleg parancsikon került-e,
- jó fájlra mutat-e,
- a felhasználó bejelentkezik-e ugyanabba a profilba,
- a Feladatütemezőben nincs-e hibás útvonal.

## Gyors fejlesztői parancsok

Receiver:

```powershell
cd C:\central_messenger
.venv\Scripts\activate
python client\receiver_client.py
```

Admin:

```powershell
cd C:\central_messenger
.venv\Scripts\activate
python client\admin_client.py
```

Build mindkettőre:

```powershell
pyinstaller --noconfirm --onefile --windowed client\receiver_client.py
pyinstaller --noconfirm --onefile --windowed client\admin_client.py
```

## Megjegyzés

A kliensoldali telepítés és futtatás szándékosan külön van választva a szerver dokumentációjától, hogy a két környezet önállóan is karbantartható legyen.
