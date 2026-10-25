; Inno Setup script for the UDM Windows installer.
; Compiled by packaging/windows/build_installer.ps1, which defines
; AppVersion, SourceDir (the PyInstaller output), IconFile, and OutputDir.

[Setup]
AppId={{6A4C3B0E-5D1F-4E7A-9B2C-8F0D1E2A3B4C}
AppName=UDM
AppVersion={#AppVersion}
AppVerName=UDM {#AppVersion}
AppPublisher=Nima Dolatabadi
AppPublisherURL=https://github.com/NimaDolatabadi/UDM
DefaultDirName={autopf}\UDM
DefaultGroupName=UDM
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutputDir}
OutputBaseFilename=UDM-{#AppVersion}-windows-x64-setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\UDM.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\UDM"; Filename: "{app}\UDM.exe"
Name: "{autodesktop}\UDM"; Filename: "{app}\UDM.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\UDM.exe"; Description: "{cm:LaunchProgram,UDM}"; Flags: nowait postinstall skipifsilent
