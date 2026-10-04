; Custom NSIS hooks for the Audook installer/uninstaller (electron-builder:
; package.json -> build.nsis.include).
;
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
!macroend
