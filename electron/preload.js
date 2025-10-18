// electron/preload.js
const { contextBridge, ipcRenderer } = require("electron");

window.addEventListener("DOMContentLoaded", () => {
  // Safe to leave empty
});

contextBridge.exposeInMainWorld("electronAPI", {
  selectFolder: () => {
    return ipcRenderer.invoke("select-folder");
  },
});

// Optional: Add a way to check if we're running in Electron
contextBridge.exposeInMainWorld("electronInfo", {
  isElectron: true,
  platform: process.platform,
  version: process.versions.electron,
});
