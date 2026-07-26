const { contextBridge, ipcRenderer } = require('electron');

// Expose IPC to renderer process
contextBridge.exposeInMainWorld('electron', {
  // App communication
  getAppConfig: () => {
    return new Promise((resolve) => {
      ipcRenderer.once('app-config', (event, data) => {
        resolve(data);
      });
      ipcRenderer.send('app-ready');
    });
  },

  // Library operations
  getBooks: () => ipcRenderer.invoke('library:getBooks'),
  searchBooks: (query) => ipcRenderer.invoke('library:searchBooks', query),
  getBookDetails: (bookId) => ipcRenderer.invoke('library:getBookDetails', bookId),

  // Player operations
  playBook: (bookId) => ipcRenderer.invoke('player:play', bookId),
  pausePlayback: () => ipcRenderer.invoke('player:pause'),
  resumePlayback: () => ipcRenderer.invoke('player:resume'),
  stopPlayback: () => ipcRenderer.invoke('player:stop'),
  seekTo: (position) => ipcRenderer.invoke('player:seek', position),
  setVolume: (volume) => ipcRenderer.invoke('player:setVolume', volume),
  setSpeed: (speed) => ipcRenderer.invoke('player:setSpeed', speed),

  // Sync operations
  syncServers: () => ipcRenderer.invoke('sync:syncServers'),

  // Native folder picker (for local audiobook folders)
  selectFolder: () => ipcRenderer.invoke('dialog:selectFolder'),

  // Custom title bar controls (the window is frameless, no native ones)
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  toggleMaximizeWindow: () => ipcRenderer.send('window:toggle-maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),
  isWindowMaximized: () => ipcRenderer.invoke('window:is-maximized'),
  onWindowMaximizedChange: (callback) => {
    ipcRenderer.on('window:maximized-change', (event, isMaximized) => callback(isMaximized));
  },

  // Listen for player events
  onPlayerState: (callback) => {
    ipcRenderer.on('player:stateChange', (event, state) => callback(state));
  },
  onPlayerPosition: (callback) => {
    ipcRenderer.on('player:position', (event, data) => callback(data));
  },

  // Detached mini-player window
  miniPlayer: {
    activate: () => ipcRenderer.send('mini-player:activate'),
    deactivate: () => ipcRenderer.send('mini-player:deactivate')
  },

  // Close-button behavior: quit, minimize to tray, or ask every time
  onCloseRequested: (callback) => {
    ipcRenderer.on('window:close-requested', () => callback());
  },
  respondToClose: (action, remember) => {
    ipcRenderer.send('window:close-response', { action, remember });
  },
  getCloseBehavior: () => ipcRenderer.invoke('settings:get-close-behavior'),
  setCloseBehavior: (action) => ipcRenderer.send('settings:set-close-behavior', action)
});
