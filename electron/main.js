const { app, BrowserWindow, ipcMain, Menu, dialog, Tray, screen, globalShortcut } = require('electron');
const path = require('path');
const fs = require('fs');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');

let mainWindow;
let miniWindow;
let tray;
let pythonProcess;
let isMiniMode = false;

const MINI_WINDOW_WIDTH = 360;
const MINI_WINDOW_HEIGHT = 210;
const BACKEND_API_BASE = 'http://127.0.0.1:5000/api';
// Matches the ±30s step used by the in-app rewind/fast-forward buttons (see
// SEEK_STEP_SECONDS in src/hooks/usePlayerState.ts) - there's no standard
// Windows media key for "seek", so Next/Previous Track double as that.
const MEDIA_KEY_SEEK_SECONDS = 30;

// Packaged apps have no visible console, so console.log/error are otherwise
// invisible to the user. Mirror backend spawn output and errors to a file
// under userData so a failure to start can actually be diagnosed.
const logFilePath = path.join(app.getPath('userData'), 'backend.log');
function logToFile(line) {
  try {
    fs.appendFileSync(logFilePath, `[${new Date().toISOString()}] ${line}\n`);
  } catch (err) {
    // Nothing we can do if even the log file can't be written.
  }
}

// Small persisted preferences file (not the audiobook library - that lives in
// the Python backend's own database). Currently just the close-button
// behavior, but a plain JSON blob under userData is easy to grow later.
const settingsFilePath = path.join(app.getPath('userData'), 'app-settings.json');

function loadSettings() {
  try {
    return JSON.parse(fs.readFileSync(settingsFilePath, 'utf8'));
  } catch (err) {
    return {};
  }
}

function saveSettings(partial) {
  try {
    fs.writeFileSync(settingsFilePath, JSON.stringify({ ...loadSettings(), ...partial }, null, 2));
  } catch (err) {
    logToFile(`Failed to save settings: ${err}`);
  }
}

// 'ask' (default) | 'quit' | 'tray' - what the close button does, see the
// mainWindow 'close' handler in createWindow() below.
let closeBehavior = loadSettings().closeBehavior || 'ask';

// Spawn Python backend
function startPythonBackend() {
  logToFile('--- startPythonBackend ---');

  if (isDev) {
    // Development: run Python directly
    const pythonScript = path.join(__dirname, '../audook_backend.py');
    pythonProcess = spawn('python', [pythonScript], {
      detached: false,
      stdio: 'pipe'
    });

    pythonProcess.stdout?.on('data', (data) => {
      console.log(`[Python Backend] ${data}`);
    });

    pythonProcess.stderr?.on('data', (data) => {
      console.error(`[Python Backend] ${data}`);
    });
  } else {
    // Production: use PyInstaller bundle
    const pythonExe = path.join(process.resourcesPath, 'audook_backend.exe');
    logToFile(`Resolved backend path: ${pythonExe}`);

    if (!fs.existsSync(pythonExe)) {
      // Common cause on Windows: antivirus / Defender silently quarantined or
      // deleted the unsigned PyInstaller executable after install.
      const message =
        `Le fichier backend est introuvable :\n${pythonExe}\n\n` +
        `Il a peut-être été supprimé ou mis en quarantaine par un antivirus ` +
        `(fréquent avec les .exe PyInstaller non signés). Vérifiez les ` +
        `quarantaines de Windows Defender / de votre antivirus, ou réinstallez Audook.`;
      logToFile(`ERROR: backend executable missing at ${pythonExe}`);
      dialog.showErrorBox('Backend Audook introuvable', message);
      return;
    }

    try {
      pythonProcess = spawn(pythonExe, [], {
        detached: false,
        stdio: 'pipe'
      });

      pythonProcess.stdout?.on('data', (data) => {
        logToFile(`[stdout] ${data}`);
      });

      pythonProcess.stderr?.on('data', (data) => {
        logToFile(`[stderr] ${data}`);
      });
    } catch (err) {
      logToFile(`Failed to spawn backend: ${err}`);
      console.error('Failed to start Python backend from:', pythonExe);
      console.error('Error:', err);
    }
  }

  pythonProcess?.on('error', (err) => {
    logToFile(`Backend process error: ${err}`);
    console.error('Python backend process error:', err);

    if (!isDev && err.code === 'ENOENT') {
      dialog.showErrorBox(
        'Backend Audook introuvable',
        "Le processus backend n'a pas pu démarrer (fichier introuvable). " +
        'Vérifiez les quarantaines de votre antivirus ou réinstallez Audook.'
      );
    }
  });

  pythonProcess?.on('exit', (code) => {
    logToFile(`Backend exited with code ${code}`);
    console.log(`Python backend exited with code ${code}`);
  });
}

// Resolves the app URL for a given hash route (e.g. '' for the main window,
// '/mini' for the detached mini-player window). Both dev and packaged builds
// use HashRouter, so the route is just appended as a URL fragment.
function resolveAppUrl(hashRoute = '') {
  const base = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '../build/index.html')}`;
  return `${base}#${hashRoute}`;
}

// Create window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    frame: false,
    show: false,
    webPreferences: {
      contextIsolation: true,
      enableRemoteModule: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../assets/icons/audook.ico')
  });

  mainWindow.loadURL(resolveAppUrl());

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Frameless window: open maximized ("plein fenêtre") instead of a fixed
  // size, and only reveal once ready to avoid a flash of an unmaximized frame.
  mainWindow.once('ready-to-show', () => {
    mainWindow.maximize();
    mainWindow.show();
  });

  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('window:maximized-change', true);
  });

  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('window:maximized-change', false);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Intercepts every close attempt (custom title bar button, Alt+F4, the
  // taskbar's own "Close window"). isQuitting is only true once app.quit()
  // has actually been decided (tray "Quitter", or the dialog's "Fermer"
  // choice below) - in that case let it proceed uninterrupted.
  mainWindow.on('close', (event) => {
    if (isQuitting) return;

    if (closeBehavior === 'tray') {
      event.preventDefault();
      mainWindow.hide();
      return;
    }
    if (closeBehavior === 'quit') {
      return;
    }

    // 'ask': hold off and let the renderer show the choice dialog instead.
    event.preventDefault();
    mainWindow.webContents.send('window:close-requested');
  });
}

// Small always-on-top window showing only the player, used when the user
// wants to keep listening without the full library window taking up space.
function createMiniWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  miniWindow = new BrowserWindow({
    width: MINI_WINDOW_WIDTH,
    height: MINI_WINDOW_HEIGHT,
    x: screenWidth - MINI_WINDOW_WIDTH - 16,
    y: screenHeight - MINI_WINDOW_HEIGHT - 16,
    frame: false,
    show: false,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      contextIsolation: true,
      enableRemoteModule: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../assets/icons/audook.ico')
  });

  miniWindow.loadURL(resolveAppUrl('/mini'));

  miniWindow.once('ready-to-show', () => {
    miniWindow.show();
  });

  // Covers both the renderer's own restore button and the OS-level close
  // (e.g. Alt+F4) - either way, falling back to the main window is correct.
  miniWindow.on('closed', () => {
    miniWindow = null;
    if (isMiniMode) {
      exitMiniMode();
    }
  });
}

function enterMiniMode() {
  if (isMiniMode) {
    miniWindow?.focus();
    return;
  }
  isMiniMode = true;
  createMiniWindow();
  mainWindow?.hide();
  updateTrayMenu();
}

function exitMiniMode() {
  isMiniMode = false;
  if (isQuitting) {
    // The mini window closing as part of app.quit()'s teardown also lands
    // here (see the 'closed' handler above) - don't pop the main window back
    // up or touch the tray (already destroyed by then) on the way out.
    return;
  }
  if (miniWindow) {
    // Triggers the 'closed' handler above, but the isMiniMode flag is already
    // false by then so it won't recurse back into exitMiniMode().
    miniWindow.close();
  }
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  } else {
    createWindow();
  }
  updateTrayMenu();
}

// Brings the app back regardless of *why* there's no visible window right
// now - detached mini-player, or closed-to-tray via the close dialog/setting.
// This is what the tray icon's own click should always do; the two states
// need different teardown (exitMiniMode also closes the mini window) so they
// can't just both be "mainWindow.show()".
function restoreMainWindow() {
  if (isMiniMode) {
    exitMiniMode();
    return;
  }
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  } else {
    createWindow();
  }
}

// Windows media keys (play/pause, next/previous track on keyboards and
// headsets) - registered globally so they work regardless of which window
// has focus, or even if Audook has no visible window at all (tray/mini
// mode). Talks straight to the Python backend's HTTP API rather than routing
// through a renderer, since there may not be a visible one listening.
async function mediaKeyPlayPause() {
  try {
    const stateRes = await fetch(`${BACKEND_API_BASE}/player/state`);
    const state = await stateRes.json();
    await fetch(`${BACKEND_API_BASE}/player/${state.is_playing ? 'pause' : 'resume'}`, { method: 'POST' });
  } catch (err) {
    logToFile(`Media key play/pause failed: ${err}`);
  }
}

async function mediaKeySeek(deltaSeconds) {
  try {
    const stateRes = await fetch(`${BACKEND_API_BASE}/player/state`);
    const state = await stateRes.json();
    const newPosition = Math.max(0, Math.min(state.duration ?? 0, (state.position ?? 0) + deltaSeconds));
    await fetch(`${BACKEND_API_BASE}/player/seek`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: newPosition })
    });
  } catch (err) {
    logToFile(`Media key seek failed: ${err}`);
  }
}

function registerMediaKeys() {
  const bindings = {
    MediaPlayPause: mediaKeyPlayPause,
    MediaNextTrack: () => mediaKeySeek(MEDIA_KEY_SEEK_SECONDS),
    MediaPreviousTrack: () => mediaKeySeek(-MEDIA_KEY_SEEK_SECONDS)
  };
  for (const [accelerator, handler] of Object.entries(bindings)) {
    // register() returns false (doesn't throw) if another app already
    // claimed the key - log and move on rather than treating it as fatal.
    const ok = globalShortcut.register(accelerator, handler);
    if (!ok) {
      logToFile(`Failed to register media key ${accelerator} (likely claimed by another app)`);
    }
  }
}

function createTray() {
  // Tray() throws (and takes down the whole main process, unlike a
  // BrowserWindow icon which just fails silently) if the icon can't be
  // loaded - e.g. a packaging config that doesn't ship assets/icons. The
  // systray is a convenience, not core functionality, so degrade instead of
  // crashing the app over it.
  try {
    tray = new Tray(path.join(__dirname, '../assets/icons/audook.ico'));
  } catch (err) {
    logToFile(`Failed to create tray icon (continuing without it): ${err}`);
    return;
  }
  tray.setToolTip('Audook');
  tray.on('click', () => restoreMainWindow());
  updateTrayMenu();
}

function updateTrayMenu() {
  if (!tray) return;
  const contextMenu = Menu.buildFromTemplate([
    {
      label: isMiniMode ? 'Fermer le mini-lecteur' : 'Ouvrir le mini-lecteur',
      click: () => (isMiniMode ? exitMiniMode() : enterMiniMode())
    },
    { label: 'Afficher Audook', click: () => restoreMainWindow() },
    { type: 'separator' },
    { label: 'Quitter', click: () => app.quit() }
  ]);
  tray.setContextMenu(contextMenu);
}

// App events
app.on('ready', () => {
  // Frameless window: no native title bar means no native menu bar either;
  // the app has its own custom title bar (see TitleBar.tsx) instead.
  Menu.setApplicationMenu(null);
  startPythonBackend();
  createWindow();
  createTray();
  registerMediaKeys();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

function killPythonBackend() {
  if (!pythonProcess || pythonProcess.killed) {
    return;
  }

  if (process.platform === 'win32') {
    if (!isDev) {
      // The packaged backend is a PyInstaller --onefile .exe: what we
      // spawned is only a bootloader that self-extracts to a temp folder
      // and launches a second process to actually run Flask/VLC, then waits
      // on it. Killing the bootloader's PID (even with /T for its tree)
      // doesn't reliably take the re-exec'd worker down with it, since
      // Windows has no parent-death cascade - it survives as an orphan
      // still holding port 5000, which is the "it disappears, then comes
      // back" this fixes. Killing by image name catches every instance
      // (bootloader and worker share the same exe name) regardless of
      // which temp path spawned it.
      spawn('taskkill', ['/im', 'audook_backend.exe', '/f', '/t']);
      return;
    }
    // Dev mode: a plain `python audook_backend.py`, no bootloader/child
    // indirection - kill by PID like before (by image name here would risk
    // killing unrelated python.exe processes elsewhere on the system).
    spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
  } else {
    pythonProcess.kill();
  }
}

// Give the backend a brief chance to close out the current reading session
// (accurate end time/position) before force-killing it. If it's unreachable
// or slow, we just proceed to the force-kill anyway - the periodic
// checkpoint (every few seconds during playback) already limits how much
// could be lost.
async function gracefulShutdown() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1500);
    await fetch(`${BACKEND_API_BASE}/shutdown`, { method: 'POST', signal: controller.signal });
    clearTimeout(timeout);
  } catch (err) {
    logToFile(`Graceful shutdown request failed (continuing anyway): ${err}`);
  }
  killPythonBackend();
}

let isQuitting = false;

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', (event) => {
  if (isQuitting) {
    return;
  }
  event.preventDefault();
  isQuitting = true;
  tray?.destroy();
  tray = null;
  gracefulShutdown().then(() => app.quit());
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// IPC handlers
ipcMain.on('app-ready', (event) => {
  event.reply('app-config', {
    isDev,
    platform: process.platform
  });
});

ipcMain.handle('dialog:selectFolder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// Custom title bar controls (frameless window has no native ones)
ipcMain.on('window:minimize', () => {
  mainWindow?.minimize();
});

ipcMain.on('window:toggle-maximize', () => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
});

ipcMain.on('window:close', () => {
  mainWindow?.close();
});

ipcMain.handle('window:is-maximized', () => {
  return mainWindow?.isMaximized() ?? false;
});

// Detached mini-player window (see createMiniWindow/enterMiniMode above)
ipcMain.on('mini-player:activate', () => enterMiniMode());
ipcMain.on('mini-player:deactivate', () => exitMiniMode());

// Close-button behavior (see the mainWindow 'close' handler in createWindow)
ipcMain.on('window:close-response', (event, { action, remember }) => {
  if (remember) {
    closeBehavior = action;
    saveSettings({ closeBehavior: action });
  }
  if (action === 'quit') {
    app.quit();
  } else {
    mainWindow?.hide();
  }
});

ipcMain.handle('settings:get-close-behavior', () => closeBehavior);
ipcMain.on('settings:set-close-behavior', (event, action) => {
  closeBehavior = action;
  saveSettings({ closeBehavior: action });
});
