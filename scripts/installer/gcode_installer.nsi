; NSIS installer script for Gcode-Generator
; Usage:
;   makensis /DOUTDIR="output_dir" /DDISTPATH="C:\path\to\dist" gcode_installer.nsi

!define APP_NAME "Gcode-Generator"
!define APP_VERSION "1.0"
!define INSTALL_DIR_REGKEY "Software\${APP_NAME}"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${APP_NAME}-Setup.exe"
InstallDir "$PROGRAMFILES\\${APP_NAME}"
ShowInstDetails show

Section "Install"
  SetOutPath "$INSTDIR"
  ; Files are copied from DistPath passed by makensis /DDISTPATH
  File /r "${DISTPATH}\\*"

  CreateShortcut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk" "$INSTDIR\\GUI.exe"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\\GUI.exe"
  RMDir /r "$INSTDIR"
  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\\${APP_NAME}"
SectionEnd
