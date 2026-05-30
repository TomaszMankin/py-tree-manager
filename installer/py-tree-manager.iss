#define MyAppName "PyTreeManager"
#define MyAppVersion "1.0.0"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Tomasz Mankin
AppPublisherURL=https://github.com/TomaszMankin/py-tree-manager
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\PyTreeManager
DisableDirPage=yes
OutputBaseFilename=PyTreeManager-Setup-{#MyAppVersion}
OutputDir=..\dist
SourceDir=..
Compression=lzma
SolidCompression=yes
UninstallDisplayName={#MyAppName}
WizardStyle=modern

[Files]
Source: "dist\PyTreeManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".pipelines\update.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\PyTreeManager.exe"
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\PyTreeManager.exe"

[Run]
Filename: "{app}\PyTreeManager.exe"; Description: "Uruchom {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the executable and update helper; tree data (user-chosen folder) is NOT touched.
Type: files; Name: "{app}\PyTreeManager.exe"
Type: files; Name: "{app}\update.bat"
