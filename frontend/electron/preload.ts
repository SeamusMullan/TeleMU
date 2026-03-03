/** Electron preload script — exposes safe APIs to renderer. */

import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("telemu", {
  platform: process.platform,
  isElectron: true,

  /** Update tray icon/menu to reflect current status. */
  updateTrayStatus: (status: { connected: boolean; recording: boolean }) => {
    ipcRenderer.send("tray:update-status", status);
  },

  /** Show a native OS notification via the tray. */
  notify: (title: string, body: string) => {
    ipcRenderer.send("tray:notify", { title, body });
  },

  /** Set whether closing the window minimizes to tray. */
  setMinimizeToTray: (value: boolean) => {
    ipcRenderer.send("tray:set-minimize-to-tray", value);
  },

  /** Set whether the app starts minimized to tray. */
  setStartMinimized: (value: boolean) => {
    ipcRenderer.send("tray:set-start-minimized", value);
  },

  /** Listen for tray menu actions sent from the main process. */
  onToggleRecording: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("tray:toggle-recording", handler);
    return () => { ipcRenderer.off("tray:toggle-recording", handler); };
  },

  onToggleConnection: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("tray:toggle-connection", handler);
    return () => { ipcRenderer.off("tray:toggle-connection", handler); };
  },
});
