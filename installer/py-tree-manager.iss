#define MyAppName "PyTreeManager"
#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif
#ifndef OutputDir
#define OutputDir "..\dist"
#endif

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Tomasz Mankin
AppPublisherURL=https://github.com/TomaszMankin/py-tree-manager
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\PyTreeManager
DisableDirPage=yes
OutputBaseFilename=PyTreeManager-Setup-{#MyAppVersion}
OutputDir={#OutputDir}
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
