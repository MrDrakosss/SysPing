[Setup]
AppName=SysPing
AppVersion=1.0.0
DefaultDirName={pf}\SysPing
DefaultGroupName=SysPing
UninstallDisplayIcon={app}\SysPingReceiver.exe
OutputDir=output
OutputBaseFilename=SysPingInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\SysPingReceiver.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "install_config_template.xml"; DestDir: "{commonappdata}\SysPing"; DestName: "config.xml"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\SysPing Receiver"; Filename: "{app}\SysPingReceiver.exe"
Name: "{group}\SysPing Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\SysPingReceiver.exe"; Description: "SysPing indítása"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{commonappdata}\SysPing\cache.json"