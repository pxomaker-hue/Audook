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

  // Listen for player events
  onPlayerState: (callback) => {
    ipcRenderer.on('player:stateChange', (event, state) => callback(state));
  },
  onPlayerPosition: (callback) => {
    ipcRenderer.on('player:position', (event, data) => callback(data));
  }
});
