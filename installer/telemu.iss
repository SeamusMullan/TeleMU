; TeleMU Inno Setup Script
; Packages the Electron app (with bundled backend) into a Windows installer.
; Build with: ISCC /DAppVersion=x.y.z telemu.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{E8751A00-TELE-MU00-0000-000000000001}
AppName=TeleMU
AppVersion={#AppVersion}
AppVerName=TeleMU {#AppVersion}
AppPublisher=TeleMU
AppPublisherURL=https://github.com/SeamusMullan/TeleMU
AppSupportURL=https://github.com/SeamusMullan/TeleMU/issues
DefaultDirName={autopf}\TeleMU
DefaultGroupName=TeleMU
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=TeleMU-Setup-v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\TeleMU.exe
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The entire unpacked electron-builder output
Source: "..\frontend\dist\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\TeleMU"; Filename: "{app}\TeleMU.exe"
Name: "{group}\Uninstall TeleMU"; Filename: "{uninstallexe}"
Name: "{autodesktop}\TeleMU"; Filename: "{app}\TeleMU.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TeleMU.exe"; Description: "Launch TeleMU"; Flags: nowait postinstall skipifsilent
