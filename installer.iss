; Inno Setup script for Audook
; Save this as installer.iss and compile with Inno Setup

[Setup]
AppName=Audook
AppVersion=1.0.0
AppPublisher=Audook Team
AppPublisherURL=https://github.com/pxomaker-hue/Audook
AppExeName=Audook.exe
DefaultDirName={pf}\Audook
DefaultGroupName=Audook
OutputDir=dist
OutputBaseFilename=Audook_Setup
Compression=lzma
SolidCompression=yes
InternalCompressLevel=ultra64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
Source: "dist\Audook.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs
Source: "README.md"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\Audook"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\Audook"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userquicklaunch}\Audook"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch Audook"; Flags: nowait postinstall skipifsilent

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
 // Show completion message
 MsgBox('Audook has been installed successfully!', mbInformation, MB_OK);
 end;
end;
