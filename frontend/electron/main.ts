/** Electron main process — window management, tray, IPC. */

import { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain, Notification } from "electron";
import path from "path";

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let isQuitting = false;
let minimizeToTray = true;
let startMinimized = false;

/** Current status used by tray icon and context menu. */
let trayStatus: { connected: boolean; recording: boolean } = {
  connected: false,
  recording: false,
};

/* ------------------------------------------------------------------ */
/*  Icon helpers                                                       */
/* ------------------------------------------------------------------ */

function getIconPath(name: string): string {
  return path.join(__dirname, "icons", name);
}

function getTrayIcon(): Electron.NativeImage {
  let iconName: string;
  if (trayStatus.recording) {
    iconName = "tray-recording.png";
  } else if (trayStatus.connected) {
    iconName = "tray-connected.png";
  } else {
    iconName = "tray-disconnected.png";
  }
  return nativeImage.createFromPath(getIconPath(iconName));
}

function getTrayTooltip(): string {
  const parts = ["TeleMU"];
  parts.push(trayStatus.connected ? "Connected" : "Disconnected");
  if (trayStatus.recording) parts.push("Recording");
  return parts.join(" — ");
}

/* ------------------------------------------------------------------ */
/*  Context menu                                                       */
/* ------------------------------------------------------------------ */

function buildTrayMenu(): Menu {
  return Menu.buildFromTemplate([
    {
      label: trayStatus.recording ? "Stop Recording" : "Start Recording",
      click: () => {
        mainWindow?.webContents.send("tray:toggle-recording");
      },
    },
    {
      label: trayStatus.connected ? "Disconnect" : "Connect",
      click: () => {
        mainWindow?.webContents.send("tray:toggle-connection");
      },
    },
    { type: "separator" },
    {
      label: "Open",
      click: () => restoreWindow(),
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);
}

/* ------------------------------------------------------------------ */
/*  Tray creation                                                      */
/* ------------------------------------------------------------------ */

function createTray() {
  tray = new Tray(getTrayIcon());
  tray.setToolTip(getTrayTooltip());
  tray.setContextMenu(buildTrayMenu());

  tray.on("double-click", () => restoreWindow());
}

function updateTray() {
  if (!tray) return;
  tray.setImage(getTrayIcon());
  tray.setToolTip(getTrayTooltip());
  tray.setContextMenu(buildTrayMenu());
}

/* ------------------------------------------------------------------ */
/*  Window helpers                                                     */
/* ------------------------------------------------------------------ */

function restoreWindow() {
  if (!mainWindow) {
    createWindow();
    return;
  }
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    show: !startMinimized,
    backgroundColor: "#1a1a1a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // In dev, load from Vite dev server; in prod, load built files
  const isDev = process.env.NODE_ENV === "development";
  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  // Minimize to tray instead of closing
  mainWindow.on("close", (event) => {
    if (!isQuitting && minimizeToTray) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

/* ------------------------------------------------------------------ */
/*  IPC handlers                                                       */
/* ------------------------------------------------------------------ */

function registerIPC() {
  /** Renderer reports updated status → refresh tray icon & menu. */
  ipcMain.on("tray:update-status", (_event, status: { connected: boolean; recording: boolean }) => {
    trayStatus = status;
    updateTray();
  });

  /** Renderer asks to show a native notification. */
  ipcMain.on("tray:notify", (_event, payload: { title: string; body: string }) => {
    if (Notification.isSupported()) {
      new Notification({ title: payload.title, body: payload.body }).show();
    }
  });

  /** Renderer toggles minimizeToTray preference. */
  ipcMain.on("tray:set-minimize-to-tray", (_event, value: boolean) => {
    minimizeToTray = value;
  });

  /** Renderer toggles startMinimized preference. */
  ipcMain.on("tray:set-start-minimized", (_event, value: boolean) => {
    startMinimized = value;
  });
}

/* ------------------------------------------------------------------ */
/*  App lifecycle                                                      */
/* ------------------------------------------------------------------ */

app.whenReady().then(() => {
  registerIPC();
  createTray();
  createWindow();
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  } else {
    restoreWindow();
  }
});
