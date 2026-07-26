const { app, BrowserWindow, ipcMain, Menu, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

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

  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '../build/index.html')}`;

  mainWindow.loadURL(startUrl);

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

// App events
app.on('ready', () => {
  // Frameless window: no native title bar means no native menu bar either;
  // the app has its own custom title bar (see TitleBar.tsx) instead.
  Menu.setApplicationMenu(null);
  startPythonBackend();
  createWindow();
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

app.on('window-all-closed', () => {
  killPythonBackend();

  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', killPythonBackend);

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
