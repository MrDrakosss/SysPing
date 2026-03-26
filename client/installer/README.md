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

```bash
SysPingInstaller.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART ^
/SERVERHTTP="http://192.168.1.10:8080" ^
/SERVERWS="ws://192.168.1.10:8080/ws/client" ^
/AUTOSTART=1 ^
/STARTMINIMIZED=1
```

---

## ☁️ Intune telepítési parancs

```powershell
Start-Process -FilePath ".\SysPingInstaller.exe" -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SERVERHTTP="http://192.168.1.10:8080" /SERVERWS="ws://192.168.1.10:8080/ws/client" /AUTOSTART=1 /STARTMINIMIZED=1' -Wait
```

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
