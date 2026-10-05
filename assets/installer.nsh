; Custom NSIS hooks for the Audook installer/uninstaller (electron-builder:
; package.json -> build.nsis.include). UTF-8 WITH BOM on purpose: it contains accents.
;
; --- Texts of the welcome and finish pages ---------------------------------------
; The pages are declared by electron-builder's template BEFORE the generic customHeader
; hook, so the MUI texts are defined from inside customWelcomePage, which is expanded
; right where the welcome page is declared (the finish page comes later and reads the
; defines that exist by then).
!macro customWelcomePage
  !define MUI_WELCOMEPAGE_TITLE "Bienvenue dans l'installation d'Audook"
  !define MUI_WELCOMEPAGE_TEXT "Cet assistant installe Audook, votre lecteur d'audiolivres, sur cet ordinateur.$\r$\n$\r$\nSi Audook est déjà installé, il est simplement mis à jour : votre bibliothèque, votre progression et vos réglages sont conservés.$\r$\n$\r$\nCliquez sur Suivant pour continuer."
  !define MUI_FINISHPAGE_TITLE "Audook est installé"
  !define MUI_FINISHPAGE_TEXT "Audook est prêt à l'emploi.$\r$\n$\r$\nAu premier lancement, ajoutez votre serveur (Audiobookshelf, Plex ou un dossier local) dans les Paramètres pour retrouver vos livres."
  !define MUI_FINISHPAGE_RUN_TEXT "Lancer Audook"
  !insertmacro MUI_PAGE_WELCOME
!macroend

; --- Closing the app / not depending on the old uninstaller -------------------------
; electron-builder's stock "is the app running?" check decides with
;   (Get-CimInstance Win32_Process | ? {...}).Count -gt 0
; but for exactly ONE matching process .Count is empty, so the check says
; "not running" and nothing gets closed. Audook ships more than one process
; (Audook.exe + audook_backend.exe + helpers), and a single orphan left over -
; typically the bundled audook_backend.exe - was enough to lock its file: the
; update then failed or ended half-installed, and the only way out was
; uninstalling first. This replaces the check: stop EVERY process running from
; the install folder, then wait until the files are really released.
;
; Runs for the installer and the uninstaller (both call CHECK_APP_RUNNING).
!macro customCheckAppRunning
  DetailPrint "$(appClosing)"
  StrCpy $R1 0

  audook_close_loop:
    IntOp $R1 $R1 + 1
    ; Kill everything started from $INSTDIR (except this installer itself),
    ; then exit with the number of such processes still alive.
    nsExec::Exec `"$PowerShellPath" -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$$f = { Get-CimInstance Win32_Process | Where-Object { $$_.ExecutablePath -and $$_.ExecutablePath.StartsWith('$INSTDIR\', 'CurrentCultureIgnoreCase') -and $$_.ProcessId -ne $$PID -and $$_.ExecutablePath -ne '$EXEPATH' } }; @(& $$f) | ForEach-Object { Stop-Process -Id $$_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Milliseconds 500; exit @(& $$f).Count"`
    Pop $0
    ${If} $0 != 0
    ${AndIf} $R1 < 10
      Sleep 500
      Goto audook_close_loop
    ${EndIf}

  ${If} $0 != 0
    ; Something still holds the folder (e.g. a process running as administrator).
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(appCannotBeClosed)" /SD IDCANCEL IDRETRY audook_retry
    Quit
    audook_retry:
    StrCpy $R1 0
    Goto audook_close_loop
  ${EndIf}

  ; Don't let electron-builder run the OLD version's uninstaller before installing.
  ; In an update that uninstaller moves every file of the install folder to %TEMP% and
  ; gives up if ONE of them is held open - by an antivirus, a backup tool, a terminal
  ; or an Explorer preview, i.e. by a process outside the install folder that the
  ; check above cannot see. It then answers "cannot be closed, retry" forever, even with
  ; no Audook process left. The installer finds the old uninstaller through the
  ; UninstallString registry value; with it gone it simply installs over the existing
  ; folder (overwriting tolerates far more locks than moving) and rewrites the value.
  ; Installer only: the uninstaller itself must keep its own entry.
  !ifndef BUILD_UNINSTALLER
    DeleteRegValue SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "UninstallString"
    DeleteRegValue HKEY_CURRENT_USER "${UNINSTALL_REGISTRY_KEY}" "UninstallString"
    !ifdef UNINSTALL_REGISTRY_KEY_2
      DeleteRegValue SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY_2}" "UninstallString"
      DeleteRegValue HKEY_CURRENT_USER "${UNINSTALL_REGISTRY_KEY_2}" "UninstallString"
    !endif

    ; Older packages shipped Gradle build artifacts of @capacitor/android inside
    ; resources\app.asar.unpacked, with paths far beyond Windows' 259-character limit
    ; (the install failed at ~25% with "cannot be closed"). They are useless and ordinary
    ; deletion can't remove them: use the \\?\ prefix. The installer recreates this folder.
    nsExec::Exec '"$SYSDIR\cmd.exe" /C rd /s /q "\\?\$INSTDIR\resources\app.asar.unpacked"'
    Pop $0
  !endif
!macroend
