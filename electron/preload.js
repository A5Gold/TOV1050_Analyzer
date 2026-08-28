const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openFile: () => ipcRenderer.invoke('dialog:openFile'),
  saveFile: (data, defaultName) => ipcRenderer.invoke('dialog:saveFile', data, defaultName)
});

