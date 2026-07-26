const { app, BrowserWindow, ipcMain, Menu, dialog, Tray, screen } = require('electron');
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
const MINI_WINDOW_HEIGHT = 165;

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
  tray.on('click', () => {
    if (isMiniMode) {
      exitMiniMode();
    } else {
      enterMiniMode();
    }
  });
  updateTrayMenu();
}

function updateTrayMenu() {
  if (!tray) return;
  const contextMenu = Menu.buildFromTemplate([
    {
      label: isMiniMode ? 'Fermer le mini-lecteur' : 'Ouvrir le mini-lecteur',
      click: () => (isMiniMode ? exitMiniMode() : enterMiniMode())
    },
    { label: 'Afficher Audook', click: () => exitMiniMode() },
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
});

function killPythonBackend() {
  if (!pythonProcess || pythonProcess.killed) {
    return;
  }

  if (process.platform === 'win32') {
    // child.kill() is unreliable on Windows for processes that spawn their
    // own threads (VLC). taskkill with /T kills the whole process tree.
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
    await fetch('http://127.0.0.1:5000/api/shutdown', { method: 'POST', signal: controller.signal });
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
