; Installateur Windows de Mapping Épi (Inno Setup 6)
; Construit par .github/workflows/installateurs.yml, ou à la main sur un PC Windows :
;   iscc /DAppVersion=1.0.0 packaging\windows\mapping_epi.iss
; Prérequis : dist\Mapping Epi\ produit par PyInstaller (packaging\mapping_epi.spec).

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Mapping Épi"
#define AppExe "Mapping Epi.exe"

[Setup]
AppId={{7C2E1A54-3B9D-4F6E-9A21-5D8C0E4B7F13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Riposte MVE, RDC
DefaultDirName={autopf}\Mapping Epi
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; installation possible sans droits administrateur (dossier de l'utilisateur) ; l'utilisateur peut choisir « pour tous »
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=MappingEpi-{#AppVersion}-Windows-Installation
SetupIconFile=..\..\assets\icons\mapping_epi.ico
; page « Contrat de licence » de l'assistant (AGPL v3)
LicenseFile=..\..\LICENSE
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
Source: "..\..\dist\Mapping Epi\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent

; Les données (fiches, comptes) sont dans %LOCALAPPDATA%\Mapping Epi : la désinstallation et les mises à jour
; ne les touchent pas.
