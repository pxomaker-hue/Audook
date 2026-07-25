const { app, BrowserWindow, ipcMain, Menu, dialog } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

// Spawn Python backend
function startPythonBackend() {
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

    try {
      pythonProcess = spawn(pythonExe, [], {
        detached: false,
        stdio: 'pipe'
      });

      pythonProcess.stdout?.on('data', (data) => {
        console.log(`[Python Backend] ${data}`);
      });

      pythonProcess.stderr?.on('data', (data) => {
        console.error(`[Python Backend] ${data}`);
      });
    } catch (err) {
      console.error('Failed to start Python backend from:', pythonExe);
      console.error('Error:', err);
    }
  }

  pythonProcess?.on('error', (err) => {
    console.error('Python backend process error:', err);
  });

  pythonProcess?.on('exit', (code) => {
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

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App events
app.on('ready', () => {
  startPythonBackend();
  createWindow();
  createMenu();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }

  // Kill Python process
  if (pythonProcess) {
    pythonProcess.kill();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// Create menu
function createMenu() {
  const template = [
    {
      label: 'Audook',
      submenu: [
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' }
      ]
    }
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

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
