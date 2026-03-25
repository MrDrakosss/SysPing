# Central Messenger

Központi szerveres belső üzenetküldő rendszer admin és kliens alkalmazással.

A projekt célja, hogy a szerveren nyilvántartott gépek között lehessen központilag üzeneteket küldeni, online/offline állapotot kezelni, valamint a fontos üzeneteket kiemelten jelezni. A rendszer úgy lett kitalálva, hogy az admin oldalról ne kelljen IP-címeket kézzel megadni, hanem a szerveren ismert gépek közül lehessen választani, keresni, tömegesen üzenni, és az offline gépek is megkapják a számukra küldött üzeneteket, amikor újra online állapotba kerülnek.

## Fő funkciók

### Központi szerver
- Linuxon futó központi alkalmazás
- MySQL adatbázis használata
- ismert gépek nyilvántartása
- online/offline státusz követése
- offline üzenetsor kezelése
- kézbesítési és olvasási állapot tárolása
- admin kliens kiszolgálása API-n keresztül
- klienskapcsolatok kezelése WebSocketen

### Receiver kliens
- háttérben futó fogadó alkalmazás
- automatikus csatlakozás a szerverhez
- online státusz küldése a szervernek
- üzenetek fogadása chat-szerű nézetben
- gépenként külön beszélgetések
- Windows tray ikon
- olvasatlan üzenet jelzés
- normál üzenetnél Windows popup
- fontos üzenetnél kiemelt figyelmeztetés
- fontos, olvasatlan üzenet esetén 10 percenként ismételt értesítés

### Admin kliens
- küldés és fogadás is támogatott
- kereshető géplista a szerverről
- küldés egy vagy több gépnek
- offline gépnek küldött üzenet sorba állítása
- gépenként külön chatnézet
- ismert gépek kezelése
- tulajdonos mező kezelése
- megjegyzés mező kezelése
- már nem létező gépek törlése vagy inaktiválása

## Projektstruktúra

```text
central_messenger/
├─ README.md
├─ server/
│  ├─ README.md
│  ├─ main.py
│  ├─ db.py
│  ├─ models.py
│  ├─ schemas.py
│  └─ .env
├─ client/
│  ├─ README.md
│  ├─ common.py
│  ├─ admin_client.py
│  ├─ receiver_client.py
│  └─ assets/
├─ requirements-server.txt
└─ requirements-client.txt
```

## Melyik README mit tartalmaz

- Ez a fájl a rendszer áttekintését és a funkciókat írja le.
- A `server/README.md` a szerver telepítését, Linuxos beállítását, adatbázis konfigurációját és automatikus indulását tartalmazza.
- A `client/README.md` a kliensek telepítését, buildelését, konfigurációját és automatikus indulását tartalmazza.

## Technológiai javaslat

### Szerver
- Python
- FastAPI
- SQLAlchemy
- MySQL vagy MariaDB
- Uvicorn
- systemd Linuxon

### Kliens
- Python
- PySide6
- websocket-client
- requests
- PyInstaller

## Telepítési logika röviden

A teljes rendszer összeállításához:
1. a szerver oldalon fel kell tenni a Python környezetet és az adatbázist,
2. be kell állítani a szerver `.env` fájlját,
3. el kell indítani vagy systemd alá kell tenni a szervert,
4. a kliens oldalon fel kell tenni a kliens függőségeket,
5. be kell állítani a szerver címét a kliens konfigurációban,
6. a klienseket fejlesztői módban Pythonból vagy terítéshez EXE-ként kell futtatni.

A részletes, konkrét parancsok és konfigurációk a két almappa README fájljaiban vannak összerakva.

## Ajánlott működési folyamat

### Receiver gép
A gép indulásakor a fogadó kliens automatikusan elindul, csatlakozik a szerverhez, online státuszba kerül, majd a szerver elküldi neki az esetleg korábban sorba állított üzeneteket.

### Admin gép
Az admin kliens a szerverről lekéri az ismert gépeket, kereshető listát mutat, és az admin onnan választ címzetteket. Ha a célgép offline, az üzenet nem vész el, hanem a szerver tárolja és később kézbesíti.

## További javasolt bővítések
- jogosultságkezelés
- audit log
- kézbesítve / olvasva státusz vizuális megjelenítése
- csoportos gépkategóriák
- részleg alapú szűrés
- Active Directory integráció
- HTTPS / WSS és kliens hitelesítés

## Megjegyzés
Ez a fő README szándékosan nem ismétli végig a teljes telepítési lépéssort. A tényleges telepítési és futtatási útmutatók külön vannak bontva a `server` és `client` mappák README fájljaiba, hogy később könnyebb legyen karbantartani.
