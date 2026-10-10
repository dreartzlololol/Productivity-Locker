[Setup]
AppName=Productivity Locker
AppVersion=2.3.0
DefaultDirName={autopf}\Productivity Locker
DefaultGroupName=Productivity Locker
OutputDir=.
OutputBaseFilename=ProductivityLocker_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "ProductivityLocker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "tips.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "index.html"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Productivity Locker"; Filename: "{app}\ProductivityLocker.exe"
Name: "{commondesktop}\Productivity Locker"; Filename: "{app}\ProductivityLocker.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
