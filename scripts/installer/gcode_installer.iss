; Inno Setup script for Gcode-Generator
; Review and adapt paths/metadata before building the installer.
; Usage (after creating dist with PyInstaller):
;   iscc.exe gcode_installer.iss
;
[Setup]
AppName=Gcode-Generator
AppVersion=1.0
DefaultDirName={pf}\Gcode-Generator
DefaultGroupName=Gcode-Generator
OutputBaseFilename=Gcode-Generator-Setup
OutputDir=..\installer_output
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; DistPath is replaced by the build script when invoked via ISCC command line.
; If you run ISCC manually, set DistPath to the absolute dist folder using /D switch
; Example: iscc /DDistPath="C:\path\to\dist\Gcode-Generator" gcode_installer.iss

[Files]
; Include everything from the dist folder produced by PyInstaller
Source: "{#DistPath}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Gcode-Generator"; Filename: "{app}\GUI.exe"
Name: "{group}\Uninstall Gcode-Generator"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\GUI.exe"; Description: "Launch Gcode-Generator"; Flags: nowait postinstall skipifsilent
