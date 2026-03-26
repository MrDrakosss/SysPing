# SysPing Client Installer – Build Guide

Ez a dokumentáció a **SysPing kliens telepítő buildeléséhez** szükséges lépéseket tartalmazza Windows környezetben.

---

## 📦 Követelmények

A buildhez az alábbiak szükségesek:

- Python 3.10+  
- pip  
- Inno Setup 6  
- PyInstaller  

---

## 🐍 Python környezet előkészítése

Ajánlott virtuális környezet használata:

```bash
python -m venv .venv
```

Aktiválás:

```bash
.venv\Scripts\activate
```

---

## 📥 Szükséges Python csomagok telepítése

A projekt gyökerében:

```bash
pip install -r requirements.txt
```

Ha nincs requirements.txt, akkor minimum:

```bash
pip install PySide6 requests websockets pyinstaller
```

---

## ⚙️ PyInstaller (EXE build)

A kliensből futtatható `.exe` készítése:

```bash
pyinstaller --noconfirm --onefile --windowed --name SysPingReceiver client\receiver_client.py
```

Sikeres build után az exe itt lesz:

```
dist\SysPingReceiver.exe
```

---

## 🛠️ Inno Setup telepítése

Töltsd le és telepítsd:

https://jrsoftware.org/isdl.php

Telepítés után az alapértelmezett útvonal:

```
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

---

## 📦 Installer build

A telepítő elkészítése:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "client\installer\SysPing.iss"
```

---

## 📁 Kimenet

A kész installer itt található:

```
client\installer\output\SysPingInstaller.exe
```

---

## 🚀 Silent telepítés (központi deploy)

A telepítő támogatja a parancssori paramétereket:

```bash
SysPingInstaller.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART ^
/SERVERHTTP="http://192.168.1.10:8080" ^
/SERVERWS="ws://192.168.1.10:8080/ws/client" ^
/AUTOSTART=1 ^
/STARTMINIMIZED=1
```

### Paraméterek:

| Paraméter | Leírás |
|----------|--------|
| /SERVERHTTP | HTTP API URL |
| /SERVERWS | WebSocket URL |
| /AUTOSTART | 1 = automatikus indítás |
| /STARTMINIMIZED | 1 = háttérben indul |

---

## 🔁 Teljes build folyamat (röviden)

```bash
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name SysPingReceiver client\receiver_client.py
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "client\installer\SysPing.iss"
```

---

## ⚠️ Gyakori hibák

### ❌ "exe not found"
→ előbb futtasd a PyInstaller buildet

### ❌ pip nem elérhető
→ telepítsd:

```bash
python -m ensurepip --upgrade
```

### ❌ ISCC.exe nem található
→ ellenőrizd az Inno Setup telepítési útvonalát

---

## 💡 Tipp

Ha automatizálni akarod:

- CI/CD (GitHub Actions)
- PowerShell build script
- tömeges deploy (GPO / Intune / PDQ)

---

## 📌 Megjegyzés

Ez a README kizárólag a **kliens telepítő buildeléséhez** tartozik.  
A szerver és a teljes rendszer dokumentációja külön README fájlban található.
