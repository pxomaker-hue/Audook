; Script Inno Setup pour Audook
; Enregistrez ceci sous installer.iss et compilez avec Inno Setup

[Setup]
AppName=Audook
AppVersion=1.0.0
AppPublisher=Équipe Audook
AppPublisherURL=https://github.com/pxomaker-hue/Audook
AppExeName=Audook.exe
DefaultDirName={pf}\Audook
DefaultGroupName=Audook
OutputDir=dist
OutputBaseFilename=Audook_Installateur
Compression=lzma
SolidCompression=yes
InternalCompressLevel=ultra64

[Languages]
Name: "french"; MessagesFile: "compiler:Languages/French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le &bureau"; GroupDescription: "Icônes supplémentaires :"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Créer une icône dans le &lancement rapide"; GroupDescription: "Icônes supplémentaires :"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
Source: "dist\Audook.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs
Source: "README.md"; DestDir: "{app}"; Flags: isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\Audook"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\Audook"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userquicklaunch}\Audook"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Lancer Audook"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
 Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
 if CurStep = ssPostInstall then
 begin
 // Afficher le message de completion
 MsgBox('Audook a été installé avec succès !', mbInformation, MB_OK);
 end;
end;
