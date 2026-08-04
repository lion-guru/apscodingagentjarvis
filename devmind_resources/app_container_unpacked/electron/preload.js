const { contextBridge, ipcRenderer, webFrame } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    // ... existing apis ...
    onUpdateLog: (callback) => ipcRenderer.on('update-log', (_event, value) => callback(value)),
    // ... existing apis ...
    setZoomFactor: (factor) => webFrame.setZoomFactor(factor),
    getZoomFactor: () => webFrame.getZoomFactor(),
    invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),
    send: (channel, ...args) => ipcRenderer.send(channel, ...args),
    on: (channel, callback) => {
        const subscription = (_event, ...args) => callback(...args);
        ipcRenderer.on(channel, subscription);
        return () => ipcRenderer.removeListener(channel, subscription);
    },
    // Auto-update APIs
    onUpdateStatus: (callback) => {
        const subscription = (_event, data) => callback(data);
        ipcRenderer.on('update-status', subscription);
        return () => ipcRenderer.removeListener('update-status', subscription);
    },
    installUpdate: () => ipcRenderer.invoke('install-update'),
    checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
});
