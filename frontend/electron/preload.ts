/** Electron preload script — exposes safe APIs to renderer. */

import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("telemu", {
  platform: process.platform,
  isElectron: true,
});
