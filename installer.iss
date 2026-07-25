; Script Inno Setup pour Audook
; Enregistrez ceci sous installer.iss et compilez avec Inno Setup
; Téléchargez Inno Setup ici : https://jrsoftware.org/isinfo.php

[Setup]
; Configuration de base
AppName=Audook
AppVersion=1.0.0
AppPublisher=Équipe Audook
AppPublisherURL=https://github.com/pxomaker-hue/Audook
AppExeName=Audook.exe

; Dossiers et fichiers
DefaultDirName={pf}\Audook
DefaultGroupName=Audook
OutputDir=dist
OutputBaseFilename=Audook_Setup

; Compression
Compression=lzma
SolidCompression=yes
InternalCompressLevel=ultra64

; Langue
[Languages]
Name: "french"; MessagesFile: "compiler:Languages/French.isl"

; Tâches (options d'installation)
[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le &bureau"; GroupDescription: "Icônes supplémentaires :"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Créer une icône dans la barre de &lancement rapide"; GroupDescription: "Icônes supplémentaires :"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "startmenuicon"; Description: "Créer une icône dans le menu &Démarrer"; GroupDescription: "Icônes supplémentaires :"; Flags: unchecked

; Fichiers à inclure
[Files]
; Exécutable principal
Source: "dist\Audook.exe"; DestDir: "{app}"; Flags: ignoreversion

; Dossier assets (icônes, images, etc.)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: isreadme
Source: "CHANGELOG.md"; DestDir: "{app}"
Source: "CONTRIBUTING.md"; DestDir: "{app}"

; Icônes
[Icons]
; Icône dans le menu Démarrer
Name: "{group}\Audook"; Filename: "{app}\{#AppExeName}"
; Icône sur le bureau
Name: "{commondesktop}\Audook"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
; Icône dans la barre de lancement rapide
Name: "{userquicklaunch}\Audook"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

; Exécution après installation
[Run]
Filename: "{app}\{#AppExeName}"; Description: "Lancer Audook"; Flags: nowait postinstall skipifsilent

; Nettoyage à la désinstallation
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; Code personnalisé
[Code]
function InitializeSetup(): Boolean;
begin
 Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
 if CurStep = ssPostInstall then
 begin
 // Afficher un message de succès
 MsgBox('Audook a été installé avec succès !' + #13#10 + #13#10 + 
        'Vous pouvez maintenant lancer Audook depuis le menu Démarrer.', 
        mbInformation, MB_OK);
 end;
end;
