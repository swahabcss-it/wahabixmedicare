; ============================================================================
; Wahabix Medicare Solution — Windows Installer Script
; ============================================================================
; This is an Inno Setup script (.iss), NOT a compiled .exe yet.
;
; HOW TO TURN THIS INTO A REAL .exe (one-time, ~2 minutes):
;   1. Download & install Inno Setup (free, official tool):
;      https://jrsoftware.org/isdl.php
;   2. Right-click this file -> "Compile" (or open it in Inno Setup and
;      press Ctrl+F9).
;   3. Your installer will appear at: installer/Output/WMS_Setup.exe
;
; WHAT THIS INSTALLER DOES:
;   - Asks for the password below before it will proceed (Setup.Password)
;   - Requests admin rights (required to install into Program Files)
;   - Copies the whole "wms" project folder to the install directory
;   - Creates Desktop + Start Menu shortcuts that run START_HERE_WINDOWS.bat
;   - Does NOT hide, lock, or restrict the source code in any way — the
;     password only gates the INSTALLER itself (who is allowed to install
;     it on this machine), same as any normal commercial software installer.
;     Once installed, all source files are plain, readable, editable — as
;     they should be for software you own and run on your own server.
; ============================================================================

#define MyAppName "Wahabix Medicare Solution"
#define MyAppVersion "3.0"
#define MyAppPublisher "WAHABIX (Shah Abdul Wahab)"
#define MyAppExeName "START_HERE_WINDOWS.bat"

[Setup]
AppId={{8F2C9A10-4B3E-4D7A-9C1F-WAHABIXMEDICARE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\WahabixMedicare
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=WMS_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
; Installer prompts for this password before Setup will continue.
; Change it here any time by editing this line and recompiling.
Password=W@hab786
Encryption=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Copies everything in the wms/ project folder (run this .iss from inside
; the installer/ folder, sitting next to the wms/ project folder).
Source: "..\wms\*"; DestDir: "{app}\wms"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Start Wahabix Medicare"; Filename: "{app}\wms\{#MyAppExeName}"; WorkingDir: "{app}\wms"
Name: "{autodesktop}\Wahabix Medicare"; Filename: "{app}\wms\{#MyAppExeName}"; WorkingDir: "{app}\wms"; Tasks: desktopicon

[Run]
Filename: "{app}\wms\{#MyAppExeName}"; Description: "Launch Wahabix Medicare Solution now"; Flags: postinstall skipifsilent shellexec

[Messages]
WelcomeLabel2=This will install {#MyAppName} version {#MyAppVersion} on your computer.%n%nRequires Python 3.11+ already installed (the app installs its own dependencies automatically on first run).
