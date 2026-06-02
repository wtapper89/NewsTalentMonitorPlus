#define MyAppName "News Talent Monitor+"
#define MyAppPublisher "News Talent Monitor+ Contributors"
#define MyAppExeName "NewsTalentMonitor.exe"
#define MyAppVersion "0.1.0"

[Setup]
AppId={{C3D3B7A8-22E3-4E5D-A4BB-2B9873B1F985}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\NewsTalentMonitorPlus
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\windows-installer
OutputBaseFilename=NewsTalentMonitorPlus-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\..\dist\windows\NewsTalentMonitor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "runtime\*"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\News Talent Monitor+ Display"; Filename: "{app}\Open Display.bat"; WorkingDir: "{app}"
Name: "{group}\News Talent Monitor+ Config"; Filename: "{app}\Open Config.bat"; WorkingDir: "{app}"
Name: "{group}\Start News Talent Monitor+"; Filename: "{app}\Start News Talent Monitor.bat"; WorkingDir: "{app}"
Name: "{group}\Stop News Talent Monitor+"; Filename: "{app}\Stop News Talent Monitor.bat"; WorkingDir: "{app}"
Name: "{group}\Check NDI Runtime"; Filename: "{app}\Check NDI Runtime.bat"; WorkingDir: "{app}"
Name: "{group}\Install NDI Runtime"; Filename: "{app}\Install NDI Runtime.bat"; WorkingDir: "{app}"
Name: "{userdesktop}\News Talent Monitor+ Display"; Filename: "{app}\Open Display.bat"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userdesktop}\News Talent Monitor+ Config"; Filename: "{app}\Open Config.bat"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\News Talent Monitor+"; Filename: "{app}\Start News Talent Monitor Hidden.vbs"; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Run]
Filename: "{app}\Install NDI Runtime.bat"; Description: "Download and install the official NDI runtime"; Flags: postinstall waituntilterminated skipifsilent unchecked; Check: IsNdiRuntimeMissing
Filename: "{app}\Check NDI Runtime.bat"; Description: "Check NDI runtime now"; Flags: postinstall skipifsilent
Filename: "{win}\System32\wscript.exe"; Parameters: """{app}\Start News Talent Monitor Hidden.vbs"""; Description: "Start News Talent Monitor+ now"; Flags: postinstall nowait skipifsilent
Filename: "{app}\Open Config.bat"; Description: "Open the config page"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /F /IM NewsTalentMonitor.exe"; Flags: runhidden

[Code]
function IsNdiRuntimeMissing: Boolean;
begin
  Result :=
    not FileExists('C:\Program Files\NDI\NDI 6 Runtime\v6\Processing.NDI.Lib.x64.dll') and
    not FileExists('C:\Program Files\NDI\NDI 5 Runtime\v5\Processing.NDI.Lib.x64.dll') and
    not FileExists('C:\Program Files\NDI\NDI 5 Tools\Runtime\Processing.NDI.Lib.x64.dll');
end;
