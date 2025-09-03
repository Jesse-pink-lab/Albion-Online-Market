#define MyAppName "Albion Trade Optimizer"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "Your Name/Org"
#define MyAppURL "https://github.com/Jesse-pink-lab/Albion-Online-Market"
#define MyAppExeName "AlbionTradeOptimizer.exe"

[Setup]
AppId={{8F7EDB67-8F55-4D53-9E5B-1B7AA9A2D5E3}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=dist\installer
OutputBaseFilename=AlbionTradeOptimizer-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=resources\icon.ico
UsePreviousLanguage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Include the PyInstaller output
Source: "dist\AlbionTradeOptimizer\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Dirs]
; Create user data dirs and keep them on uninstall
Name: "{userappdata}\AlbionTradeOptimizer";       Flags: uninsneveruninstall
Name: "{userappdata}\AlbionTradeOptimizer\logs";  Flags: uninsneveruninstall
Name: "{userappdata}\AlbionTradeOptimizer\data";  Flags: uninsneveruninstall
Name: "{userappdata}\AlbionTradeOptimizer\bin";   Flags: uninsneveruninstall

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Icons]
Name: "{group}\{#MyAppName}";       Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
