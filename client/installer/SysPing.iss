[Setup]
AppName=SysPing
AppVersion=1.0.0
DefaultDirName={autopf}\SysPing
DefaultGroupName=SysPing
UninstallDisplayIcon={app}\SysPingReceiver.exe
OutputDir=output
OutputBaseFilename=SysPingInstaller
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Files]
Source: "..\..\dist\SysPingReceiver.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SysPing Receiver"; Filename: "{app}\SysPingReceiver.exe"
Name: "{group}\SysPing Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\SysPingReceiver.exe"; Description: "SysPing indítása"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\SysPing"

[Code]
var
  ConfigPage: TWizardPage;
  HttpUrlEdit: TEdit;
  WsUrlEdit: TEdit;
  AutoStartCheck: TNewCheckBox;
  StartMinimizedCheck: TNewCheckBox;

function XmlEscape(Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '&', '&amp;', True);
  StringChangeEx(Result, '<', '&lt;', True);
  StringChangeEx(Result, '>', '&gt;', True);
  StringChangeEx(Result, '"', '&quot;', True);
  StringChangeEx(Result, '''', '&apos;', True);
end;

function BoolToXml(Value: Boolean): String;
begin
  if Value then
    Result := 'true'
  else
    Result := 'false';
end;

function GetCmdValue(const ParamName: String): String;
var
  I: Integer;
  Prefix: String;
  Current: String;
begin
  Result := '';
  Prefix := '/' + Uppercase(ParamName) + '=';

  for I := 1 to ParamCount do
  begin
    Current := ParamStr(I);
    if Pos(Prefix, Uppercase(Current)) = 1 then
    begin
      Result := Copy(Current, Length(Prefix) + 1, MaxInt);
      Exit;
    end;
  end;
end;

function GetConfiguredHttpUrl(): String;
begin
  Result := Trim(GetCmdValue('SERVERHTTP'));
  if Result = '' then
    Result := Trim(HttpUrlEdit.Text);
end;

function GetConfiguredWsUrl(): String;
begin
  Result := Trim(GetCmdValue('SERVERWS'));
  if Result = '' then
    Result := Trim(WsUrlEdit.Text);
end;

function GetConfiguredAutoStart(): Boolean;
var
  V: String;
begin
  V := Uppercase(Trim(GetCmdValue('AUTOSTART')));
  if V <> '' then
  begin
    Result := (V = '1') or (V = 'TRUE') or (V = 'YES');
    Exit;
  end;

  Result := AutoStartCheck.Checked;
end;

function GetConfiguredStartMinimized(): Boolean;
var
  V: String;
begin
  V := Uppercase(Trim(GetCmdValue('STARTMINIMIZED')));
  if V <> '' then
  begin
    Result := (V = '1') or (V = 'TRUE') or (V = 'YES');
    Exit;
  end;

  Result := StartMinimizedCheck.Checked;
end;

procedure SaveClientConfig();
var
  ConfigDir: String;
  ConfigPath: String;
  XmlText: String;
  HttpUrl: String;
  WsUrl: String;
  AutoStart: Boolean;
  StartMinimized: Boolean;
begin
  ConfigDir := ExpandConstant('{commonappdata}\SysPing');
  ConfigPath := ConfigDir + '\config.xml';

  if not DirExists(ConfigDir) then
    ForceDirectories(ConfigDir);

  HttpUrl := GetConfiguredHttpUrl();
  WsUrl := GetConfiguredWsUrl();
  AutoStart := GetConfiguredAutoStart();
  StartMinimized := GetConfiguredStartMinimized();

  XmlText :=
    '<?xml version="1.0" encoding="utf-8"?>' + #13#10 +
    '<SysPingConfig>' + #13#10 +
    '  <Server>' + #13#10 +
    '    <HttpUrl>' + XmlEscape(HttpUrl) + '</HttpUrl>' + #13#10 +
    '    <WsUrl>' + XmlEscape(WsUrl) + '</WsUrl>' + #13#10 +
    '  </Server>' + #13#10 +
    '  <Client>' + #13#10 +
    '    <MachineName></MachineName>' + #13#10 +
    '    <AutoStart>' + BoolToXml(AutoStart) + '</AutoStart>' + #13#10 +
    '    <StartMinimized>' + BoolToXml(StartMinimized) + '</StartMinimized>' + #13#10 +
    '  </Client>' + #13#10 +
    '</SysPingConfig>' + #13#10;

  SaveStringToFile(ConfigPath, XmlText, False);
end;

procedure SetMachineAutostart();
var
  RunValue: String;
begin
  RunValue := ExpandConstant('"{app}\SysPingReceiver.exe"');

  if GetConfiguredAutoStart() then
  begin
    RegWriteStringValue(
      HKLM,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'SysPingReceiver',
      RunValue
    );
  end
  else
  begin
    RegDeleteValue(
      HKLM,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'SysPingReceiver'
    );
  end;
end;

procedure InitializeWizard();
var
  InfoLabel: TNewStaticText;
  HttpLabel: TNewStaticText;
  WsLabel: TNewStaticText;
begin
  ConfigPage := CreateCustomPage(
    wpSelectDir,
    'SysPing kliens beállítások',
    'Add meg a szerver elérését és az indulási beállításokat.'
  );

  InfoLabel := TNewStaticText.Create(ConfigPage);
  InfoLabel.Parent := ConfigPage.Surface;
  InfoLabel.Left := ScaleX(0);
  InfoLabel.Top := ScaleY(0);
  InfoLabel.Width := ScaleX(430);
  InfoLabel.Height := ScaleY(30);
  InfoLabel.Caption := 'Ezek az értékek a ProgramData\SysPing\config.xml fájlba kerülnek.';
  InfoLabel.WordWrap := True;

  HttpLabel := TNewStaticText.Create(ConfigPage);
  HttpLabel.Parent := ConfigPage.Surface;
  HttpLabel.Left := ScaleX(0);
  HttpLabel.Top := ScaleY(42);
  HttpLabel.Caption := 'HTTP URL:';

  HttpUrlEdit := TEdit.Create(ConfigPage);
  HttpUrlEdit.Parent := ConfigPage.Surface;
  HttpUrlEdit.Left := ScaleX(0);
  HttpUrlEdit.Top := ScaleY(60);
  HttpUrlEdit.Width := ScaleX(420);
  HttpUrlEdit.Text := 'http://127.0.0.1:8080';

  WsLabel := TNewStaticText.Create(ConfigPage);
  WsLabel.Parent := ConfigPage.Surface;
  WsLabel.Left := ScaleX(0);
  WsLabel.Top := ScaleY(100);
  WsLabel.Caption := 'WebSocket URL:';

  WsUrlEdit := TEdit.Create(ConfigPage);
  WsUrlEdit.Parent := ConfigPage.Surface;
  WsUrlEdit.Left := ScaleX(0);
  WsUrlEdit.Top := ScaleY(118);
  WsUrlEdit.Width := ScaleX(420);
  WsUrlEdit.Text := 'ws://127.0.0.1:8080/ws/client';

  AutoStartCheck := TNewCheckBox.Create(ConfigPage);
  AutoStartCheck.Parent := ConfigPage.Surface;
  AutoStartCheck.Left := ScaleX(0);
  AutoStartCheck.Top := ScaleY(165);
  AutoStartCheck.Width := ScaleX(420);
  AutoStartCheck.Caption := 'Automatikus indítás minden felhasználónál';
  AutoStartCheck.Checked := True;

  StartMinimizedCheck := TNewCheckBox.Create(ConfigPage);
  StartMinimizedCheck.Parent := ConfigPage.Surface;
  StartMinimizedCheck.Left := ScaleX(0);
  StartMinimizedCheck.Top := ScaleY(190);
  StartMinimizedCheck.Width := ScaleX(420);
  StartMinimizedCheck.Caption := 'Indulás háttérben / minimalizálva';
  StartMinimizedCheck.Checked := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  HttpUrl: String;
  WsUrl: String;
begin
  Result := True;

  if CurPageID = ConfigPage.ID then
  begin
    HttpUrl := GetConfiguredHttpUrl();
    WsUrl := GetConfiguredWsUrl();

    if HttpUrl = '' then
    begin
      MsgBox('A HTTP URL mező nem lehet üres.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if WsUrl = '' then
    begin
      MsgBox('A WebSocket URL mező nem lehet üres.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    SaveClientConfig();
    SetMachineAutostart();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    Exec('taskkill', '/F /IM SysPingReceiver.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    RegDeleteValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Run', 'SysPingReceiver');
  end;
end;