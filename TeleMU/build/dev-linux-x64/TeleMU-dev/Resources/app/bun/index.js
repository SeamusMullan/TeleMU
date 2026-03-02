// @bun
var __create = Object.create;
var __getProtoOf = Object.getPrototypeOf;
var __defProp = Object.defineProperty;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __toESM = (mod, isNodeMode, target) => {
  target = mod != null ? __create(__getProtoOf(mod)) : {};
  const to = isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target;
  for (let key of __getOwnPropNames(mod))
    if (!__hasOwnProp.call(to, key))
      __defProp(to, key, {
        get: () => mod[key],
        enumerable: true
      });
  return to;
};
var __moduleCache = /* @__PURE__ */ new WeakMap;
var __toCommonJS = (from) => {
  var entry = __moduleCache.get(from), desc;
  if (entry)
    return entry;
  entry = __defProp({}, "__esModule", { value: true });
  if (from && typeof from === "object" || typeof from === "function")
    __getOwnPropNames(from).map((key) => !__hasOwnProp.call(entry, key) && __defProp(entry, key, {
      get: () => from[key],
      enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable
    }));
  __moduleCache.set(from, entry);
  return entry;
};
var __commonJS = (cb, mod) => () => (mod || cb((mod = { exports: {} }).exports, mod), mod.exports);
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, {
      get: all[name],
      enumerable: true,
      configurable: true,
      set: (newValue) => all[name] = () => newValue
    });
};
var __esm = (fn, res) => () => (fn && (res = fn(fn = 0)), res);
var __promiseAll = (args) => Promise.all(args);
var __require = import.meta.require;

// node_modules/electrobun/dist/api/bun/events/event.ts
class ElectrobunEvent {
  name;
  data;
  _response;
  responseWasSet = false;
  constructor(name, data) {
    this.name = name;
    this.data = data;
  }
  get response() {
    return this._response;
  }
  set response(value) {
    this._response = value;
    this.responseWasSet = true;
  }
  clearResponse() {
    this._response = undefined;
    this.responseWasSet = false;
  }
}

// node_modules/electrobun/dist/api/bun/events/windowEvents.ts
var windowEvents_default;
var init_windowEvents = __esm(() => {
  windowEvents_default = {
    close: (data) => new ElectrobunEvent("close", data),
    resize: (data) => new ElectrobunEvent("resize", data),
    move: (data) => new ElectrobunEvent("move", data),
    focus: (data) => new ElectrobunEvent("focus", data)
  };
});

// node_modules/electrobun/dist/api/bun/events/webviewEvents.ts
var webviewEvents_default;
var init_webviewEvents = __esm(() => {
  webviewEvents_default = {
    willNavigate: (data) => new ElectrobunEvent("will-navigate", data),
    didNavigate: (data) => new ElectrobunEvent("did-navigate", data),
    didNavigateInPage: (data) => new ElectrobunEvent("did-navigate-in-page", data),
    didCommitNavigation: (data) => new ElectrobunEvent("did-commit-navigation", data),
    domReady: (data) => new ElectrobunEvent("dom-ready", data),
    newWindowOpen: (data) => new ElectrobunEvent("new-window-open", data),
    hostMessage: (data) => new ElectrobunEvent("host-message", data),
    downloadStarted: (data) => new ElectrobunEvent("download-started", data),
    downloadProgress: (data) => new ElectrobunEvent("download-progress", data),
    downloadCompleted: (data) => new ElectrobunEvent("download-completed", data),
    downloadFailed: (data) => new ElectrobunEvent("download-failed", data)
  };
});

// node_modules/electrobun/dist/api/bun/events/trayEvents.ts
var trayEvents_default;
var init_trayEvents = __esm(() => {
  trayEvents_default = {
    trayClicked: (data) => new ElectrobunEvent("tray-clicked", data)
  };
});

// node_modules/electrobun/dist/api/bun/events/ApplicationEvents.ts
var ApplicationEvents_default;
var init_ApplicationEvents = __esm(() => {
  ApplicationEvents_default = {
    applicationMenuClicked: (data) => new ElectrobunEvent("application-menu-clicked", data),
    contextMenuClicked: (data) => new ElectrobunEvent("context-menu-clicked", data),
    openUrl: (data) => new ElectrobunEvent("open-url", data),
    beforeQuit: (data) => new ElectrobunEvent("before-quit", data)
  };
});

// node_modules/electrobun/dist/api/bun/events/eventEmitter.ts
import EventEmitter from "events";
var ElectrobunEventEmitter, electrobunEventEmitter, eventEmitter_default;
var init_eventEmitter = __esm(() => {
  init_windowEvents();
  init_webviewEvents();
  init_trayEvents();
  init_ApplicationEvents();
  ElectrobunEventEmitter = class ElectrobunEventEmitter extends EventEmitter {
    constructor() {
      super();
    }
    emitEvent(ElectrobunEvent2, specifier) {
      if (specifier) {
        this.emit(`${ElectrobunEvent2.name}-${specifier}`, ElectrobunEvent2);
      } else {
        this.emit(ElectrobunEvent2.name, ElectrobunEvent2);
      }
    }
    events = {
      window: {
        ...windowEvents_default
      },
      webview: {
        ...webviewEvents_default
      },
      tray: {
        ...trayEvents_default
      },
      app: {
        ...ApplicationEvents_default
      }
    };
  };
  electrobunEventEmitter = new ElectrobunEventEmitter;
  eventEmitter_default = electrobunEventEmitter;
});

// node_modules/electrobun/dist/api/shared/rpc.ts
function missingTransportMethodError(methods, action) {
  const methodsString = methods.map((m) => `"${m}"`).join(", ");
  return new Error(`This RPC instance cannot ${action} because the transport did not provide one or more of these methods: ${methodsString}`);
}
function createRPC(options = {}) {
  let debugHooks = {};
  let transport = {};
  let requestHandler = undefined;
  function setTransport(newTransport) {
    if (transport.unregisterHandler)
      transport.unregisterHandler();
    transport = newTransport;
    transport.registerHandler?.(handler);
  }
  function setRequestHandler(h) {
    if (typeof h === "function") {
      requestHandler = h;
      return;
    }
    requestHandler = (method, params) => {
      const handlerFn = h[method];
      if (handlerFn)
        return handlerFn(params);
      const fallbackHandler = h._;
      if (!fallbackHandler)
        throw new Error(`The requested method has no handler: ${String(method)}`);
      return fallbackHandler(method, params);
    };
  }
  const { maxRequestTime = DEFAULT_MAX_REQUEST_TIME } = options;
  if (options.transport)
    setTransport(options.transport);
  if (options.requestHandler)
    setRequestHandler(options.requestHandler);
  if (options._debugHooks)
    debugHooks = options._debugHooks;
  let lastRequestId = 0;
  function getRequestId() {
    if (lastRequestId <= MAX_ID)
      return ++lastRequestId;
    return lastRequestId = 0;
  }
  const requestListeners = new Map;
  const requestTimeouts = new Map;
  function requestFn(method, ...args) {
    const params = args[0];
    return new Promise((resolve, reject) => {
      if (!transport.send)
        throw missingTransportMethodError(["send"], "make requests");
      const requestId = getRequestId();
      const request2 = {
        type: "request",
        id: requestId,
        method,
        params
      };
      requestListeners.set(requestId, { resolve, reject });
      if (maxRequestTime !== Infinity)
        requestTimeouts.set(requestId, setTimeout(() => {
          requestTimeouts.delete(requestId);
          reject(new Error("RPC request timed out."));
        }, maxRequestTime));
      debugHooks.onSend?.(request2);
      transport.send(request2);
    });
  }
  const request = new Proxy(requestFn, {
    get: (target, prop, receiver) => {
      if (prop in target)
        return Reflect.get(target, prop, receiver);
      return (params) => requestFn(prop, params);
    }
  });
  const requestProxy = request;
  function sendFn(message, ...args) {
    const payload = args[0];
    if (!transport.send)
      throw missingTransportMethodError(["send"], "send messages");
    const rpcMessage = {
      type: "message",
      id: message,
      payload
    };
    debugHooks.onSend?.(rpcMessage);
    transport.send(rpcMessage);
  }
  const send = new Proxy(sendFn, {
    get: (target, prop, receiver) => {
      if (prop in target)
        return Reflect.get(target, prop, receiver);
      return (payload) => sendFn(prop, payload);
    }
  });
  const sendProxy = send;
  const messageListeners = new Map;
  const wildcardMessageListeners = new Set;
  function addMessageListener(message, listener) {
    if (!transport.registerHandler)
      throw missingTransportMethodError(["registerHandler"], "register message listeners");
    if (message === "*") {
      wildcardMessageListeners.add(listener);
      return;
    }
    if (!messageListeners.has(message))
      messageListeners.set(message, new Set);
    messageListeners.get(message).add(listener);
  }
  function removeMessageListener(message, listener) {
    if (message === "*") {
      wildcardMessageListeners.delete(listener);
      return;
    }
    messageListeners.get(message)?.delete(listener);
    if (messageListeners.get(message)?.size === 0)
      messageListeners.delete(message);
  }
  async function handler(message) {
    debugHooks.onReceive?.(message);
    if (!("type" in message))
      throw new Error("Message does not contain a type.");
    if (message.type === "request") {
      if (!transport.send || !requestHandler)
        throw missingTransportMethodError(["send", "requestHandler"], "handle requests");
      const { id, method, params } = message;
      let response;
      try {
        response = {
          type: "response",
          id,
          success: true,
          payload: await requestHandler(method, params)
        };
      } catch (error) {
        if (!(error instanceof Error))
          throw error;
        response = {
          type: "response",
          id,
          success: false,
          error: error.message
        };
      }
      debugHooks.onSend?.(response);
      transport.send(response);
      return;
    }
    if (message.type === "response") {
      const timeout = requestTimeouts.get(message.id);
      if (timeout != null)
        clearTimeout(timeout);
      const { resolve, reject } = requestListeners.get(message.id) ?? {};
      if (!message.success)
        reject?.(new Error(message.error));
      else
        resolve?.(message.payload);
      return;
    }
    if (message.type === "message") {
      for (const listener of wildcardMessageListeners)
        listener(message.id, message.payload);
      const listeners = messageListeners.get(message.id);
      if (!listeners)
        return;
      for (const listener of listeners)
        listener(message.payload);
      return;
    }
    throw new Error(`Unexpected RPC message type: ${message.type}`);
  }
  const proxy = { send: sendProxy, request: requestProxy };
  return {
    setTransport,
    setRequestHandler,
    request,
    requestProxy,
    send,
    sendProxy,
    addMessageListener,
    removeMessageListener,
    proxy
  };
}
function defineElectrobunRPC(_side, config) {
  const rpcOptions = {
    maxRequestTime: config.maxRequestTime,
    requestHandler: {
      ...config.handlers.requests,
      ...config.extraRequestHandlers
    },
    transport: {
      registerHandler: () => {}
    }
  };
  const rpc = createRPC(rpcOptions);
  const messageHandlers = config.handlers.messages;
  if (messageHandlers) {
    rpc.addMessageListener("*", (messageName, payload) => {
      const globalHandler = messageHandlers["*"];
      if (globalHandler) {
        globalHandler(messageName, payload);
      }
      const messageHandler = messageHandlers[messageName];
      if (messageHandler) {
        messageHandler(payload);
      }
    });
  }
  return rpc;
}
var MAX_ID = 10000000000, DEFAULT_MAX_REQUEST_TIME = 1000;

// node_modules/electrobun/dist/api/shared/platform.ts
import { platform, arch } from "os";
var platformName, archName, OS, ARCH;
var init_platform = __esm(() => {
  platformName = platform();
  archName = arch();
  OS = (() => {
    switch (platformName) {
      case "win32":
        return "win";
      case "darwin":
        return "macos";
      case "linux":
        return "linux";
      default:
        throw new Error(`Unsupported platform: ${platformName}`);
    }
  })();
  ARCH = (() => {
    if (OS === "win") {
      return "x64";
    }
    switch (archName) {
      case "arm64":
        return "arm64";
      case "x64":
        return "x64";
      default:
        throw new Error(`Unsupported architecture: ${archName}`);
    }
  })();
});

// node_modules/electrobun/dist/api/shared/naming.ts
function sanitizeAppName(appName) {
  return appName.replace(/ /g, "");
}
function getAppFileName(appName, buildEnvironment) {
  const sanitized = sanitizeAppName(appName);
  return buildEnvironment === "stable" ? sanitized : `${sanitized}-${buildEnvironment}`;
}
function getPlatformPrefix(buildEnvironment, os, arch2) {
  return `${buildEnvironment}-${os}-${arch2}`;
}
function getTarballFileName(appFileName, os) {
  return os === "macos" ? `${appFileName}.app.tar.zst` : `${appFileName}.tar.zst`;
}

// node_modules/electrobun/dist/api/bun/core/Utils.ts
var exports_Utils = {};
__export(exports_Utils, {
  showNotification: () => showNotification,
  showMessageBox: () => showMessageBox,
  showItemInFolder: () => showItemInFolder,
  quit: () => quit,
  paths: () => paths,
  openPath: () => openPath,
  openFileDialog: () => openFileDialog,
  openExternal: () => openExternal,
  moveToTrash: () => moveToTrash,
  clipboardWriteText: () => clipboardWriteText,
  clipboardWriteImage: () => clipboardWriteImage,
  clipboardReadText: () => clipboardReadText,
  clipboardReadImage: () => clipboardReadImage,
  clipboardClear: () => clipboardClear,
  clipboardAvailableFormats: () => clipboardAvailableFormats
});
import { homedir, tmpdir } from "os";
import { join } from "path";
import { readFileSync } from "fs";
function getLinuxXdgUserDirs() {
  try {
    const content = readFileSync(join(home, ".config", "user-dirs.dirs"), "utf-8");
    const dirs = {};
    for (const line of content.split(`
`)) {
      const trimmed = line.trim();
      if (trimmed.startsWith("#") || !trimmed.includes("="))
        continue;
      const eqIdx = trimmed.indexOf("=");
      const key = trimmed.slice(0, eqIdx);
      let value = trimmed.slice(eqIdx + 1);
      if (value.startsWith('"') && value.endsWith('"')) {
        value = value.slice(1, -1);
      }
      value = value.replace(/\$HOME/g, home);
      dirs[key] = value;
    }
    return dirs;
  } catch {
    return {};
  }
}
function xdgUserDir(key, fallbackName) {
  if (OS !== "linux")
    return "";
  if (!_xdgUserDirs)
    _xdgUserDirs = getLinuxXdgUserDirs();
  return _xdgUserDirs[key] || join(home, fallbackName);
}
function getVersionInfo() {
  if (_versionInfo)
    return _versionInfo;
  try {
    const resourcesDir = "Resources";
    const raw = readFileSync(join("..", resourcesDir, "version.json"), "utf-8");
    const parsed = JSON.parse(raw);
    _versionInfo = { identifier: parsed.identifier, channel: parsed.channel };
    return _versionInfo;
  } catch (error) {
    console.error("Failed to read version.json", error);
    throw error;
  }
}
function getAppDataDir() {
  switch (OS) {
    case "macos":
      return join(home, "Library", "Application Support");
    case "win":
      return process.env["LOCALAPPDATA"] || join(home, "AppData", "Local");
    case "linux":
      return process.env["XDG_DATA_HOME"] || join(home, ".local", "share");
  }
}
function getCacheDir() {
  switch (OS) {
    case "macos":
      return join(home, "Library", "Caches");
    case "win":
      return process.env["LOCALAPPDATA"] || join(home, "AppData", "Local");
    case "linux":
      return process.env["XDG_CACHE_HOME"] || join(home, ".cache");
  }
}
function getLogsDir() {
  switch (OS) {
    case "macos":
      return join(home, "Library", "Logs");
    case "win":
      return process.env["LOCALAPPDATA"] || join(home, "AppData", "Local");
    case "linux":
      return process.env["XDG_STATE_HOME"] || join(home, ".local", "state");
  }
}
function getConfigDir() {
  switch (OS) {
    case "macos":
      return join(home, "Library", "Application Support");
    case "win":
      return process.env["APPDATA"] || join(home, "AppData", "Roaming");
    case "linux":
      return process.env["XDG_CONFIG_HOME"] || join(home, ".config");
  }
}
function getUserDir(macName, winName, xdgKey, fallbackName) {
  switch (OS) {
    case "macos":
      return join(home, macName);
    case "win": {
      const userProfile = process.env["USERPROFILE"] || home;
      return join(userProfile, winName);
    }
    case "linux":
      return xdgUserDir(xdgKey, fallbackName);
  }
}
var moveToTrash = (path) => {
  return ffi.request.moveToTrash({ path });
}, showItemInFolder = (path) => {
  return ffi.request.showItemInFolder({ path });
}, openExternal = (url) => {
  return ffi.request.openExternal({ url });
}, openPath = (path) => {
  return ffi.request.openPath({ path });
}, showNotification = (options) => {
  const { title, body, subtitle, silent } = options;
  ffi.request.showNotification({ title, body, subtitle, silent });
}, isQuitting = false, quit = () => {
  if (isQuitting)
    return;
  isQuitting = true;
  const beforeQuitEvent = electrobunEventEmitter.events.app.beforeQuit({});
  electrobunEventEmitter.emitEvent(beforeQuitEvent);
  if (beforeQuitEvent.responseWasSet && beforeQuitEvent.response?.allow === false) {
    isQuitting = false;
    return;
  }
  native.symbols.stopEventLoop();
  native.symbols.waitForShutdownComplete(5000);
  native.symbols.forceExit(0);
}, openFileDialog = async (opts = {}) => {
  const optsWithDefault = {
    ...{
      startingFolder: "~/",
      allowedFileTypes: "*",
      canChooseFiles: true,
      canChooseDirectory: true,
      allowsMultipleSelection: true
    },
    ...opts
  };
  const result = await ffi.request.openFileDialog({
    startingFolder: optsWithDefault.startingFolder,
    allowedFileTypes: optsWithDefault.allowedFileTypes,
    canChooseFiles: optsWithDefault.canChooseFiles,
    canChooseDirectory: optsWithDefault.canChooseDirectory,
    allowsMultipleSelection: optsWithDefault.allowsMultipleSelection
  });
  const filePaths = result.split(",");
  return filePaths;
}, showMessageBox = async (opts = {}) => {
  const {
    type = "info",
    title = "",
    message = "",
    detail = "",
    buttons = ["OK"],
    defaultId = 0,
    cancelId = -1
  } = opts;
  const response = ffi.request.showMessageBox({
    type,
    title,
    message,
    detail,
    buttons,
    defaultId,
    cancelId
  });
  return { response };
}, clipboardReadText = () => {
  return ffi.request.clipboardReadText();
}, clipboardWriteText = (text) => {
  ffi.request.clipboardWriteText({ text });
}, clipboardReadImage = () => {
  return ffi.request.clipboardReadImage();
}, clipboardWriteImage = (pngData) => {
  ffi.request.clipboardWriteImage({ pngData });
}, clipboardClear = () => {
  ffi.request.clipboardClear();
}, clipboardAvailableFormats = () => {
  return ffi.request.clipboardAvailableFormats();
}, home, _xdgUserDirs, _versionInfo, paths;
var init_Utils = __esm(async () => {
  init_eventEmitter();
  init_platform();
  await init_native();
  process.exit = (code) => {
    if (isQuitting) {
      native.symbols.forceExit(code ?? 0);
      return;
    }
    quit();
  };
  home = homedir();
  paths = {
    get home() {
      return home;
    },
    get appData() {
      return getAppDataDir();
    },
    get config() {
      return getConfigDir();
    },
    get cache() {
      return getCacheDir();
    },
    get temp() {
      return tmpdir();
    },
    get logs() {
      return getLogsDir();
    },
    get documents() {
      return getUserDir("Documents", "Documents", "XDG_DOCUMENTS_DIR", "Documents");
    },
    get downloads() {
      return getUserDir("Downloads", "Downloads", "XDG_DOWNLOAD_DIR", "Downloads");
    },
    get desktop() {
      return getUserDir("Desktop", "Desktop", "XDG_DESKTOP_DIR", "Desktop");
    },
    get pictures() {
      return getUserDir("Pictures", "Pictures", "XDG_PICTURES_DIR", "Pictures");
    },
    get music() {
      return getUserDir("Music", "Music", "XDG_MUSIC_DIR", "Music");
    },
    get videos() {
      return getUserDir("Movies", "Videos", "XDG_VIDEOS_DIR", "Videos");
    },
    get userData() {
      const { identifier, channel } = getVersionInfo();
      return join(getAppDataDir(), identifier, channel);
    },
    get userCache() {
      const { identifier, channel } = getVersionInfo();
      return join(getCacheDir(), identifier, channel);
    },
    get userLogs() {
      const { identifier, channel } = getVersionInfo();
      return join(getLogsDir(), identifier, channel);
    }
  };
});

// node_modules/electrobun/dist/api/bun/core/Updater.ts
import { join as join2, dirname, resolve } from "path";
import { homedir as homedir2 } from "os";
import {
  renameSync,
  unlinkSync,
  mkdirSync,
  rmdirSync,
  statSync,
  readdirSync
} from "fs";
import { execSync } from "child_process";
function emitStatus(status, message, details) {
  const entry = {
    status,
    message,
    timestamp: Date.now(),
    details
  };
  statusHistory.push(entry);
  if (onStatusChangeCallback) {
    onStatusChangeCallback(entry);
  }
}
function getAppDataDir2() {
  switch (OS) {
    case "macos":
      return join2(homedir2(), "Library", "Application Support");
    case "win":
      return process.env["LOCALAPPDATA"] || join2(homedir2(), "AppData", "Local");
    case "linux":
      return process.env["XDG_DATA_HOME"] || join2(homedir2(), ".local", "share");
    default:
      return join2(homedir2(), ".config");
  }
}
function cleanupExtractionFolder(extractionFolder, keepTarHash) {
  const keepFile = `${keepTarHash}.tar`;
  try {
    const entries = readdirSync(extractionFolder);
    for (const entry of entries) {
      if (entry === keepFile)
        continue;
      const fullPath = join2(extractionFolder, entry);
      try {
        const s = statSync(fullPath);
        if (s.isDirectory()) {
          rmdirSync(fullPath, { recursive: true });
        } else {
          unlinkSync(fullPath);
        }
      } catch (e) {}
    }
  } catch (e) {}
}
var statusHistory, onStatusChangeCallback = null, localInfo, updateInfo, Updater;
var init_Updater = __esm(async () => {
  init_platform();
  await init_Utils();
  statusHistory = [];
  Updater = {
    updateInfo: () => {
      return updateInfo;
    },
    getStatusHistory: () => {
      return [...statusHistory];
    },
    clearStatusHistory: () => {
      statusHistory.length = 0;
    },
    onStatusChange: (callback) => {
      onStatusChangeCallback = callback;
    },
    checkForUpdate: async () => {
      emitStatus("checking", "Checking for updates...");
      const localInfo2 = await Updater.getLocallocalInfo();
      if (localInfo2.channel === "dev") {
        emitStatus("no-update", "Dev channel - updates disabled", {
          currentHash: localInfo2.hash
        });
        return {
          version: localInfo2.version,
          hash: localInfo2.hash,
          updateAvailable: false,
          updateReady: false,
          error: ""
        };
      }
      const cacheBuster = Math.random().toString(36).substring(7);
      const platformPrefix = getPlatformPrefix(localInfo2.channel, OS, ARCH);
      const updateInfoUrl = `${localInfo2.baseUrl.replace(/\/+$/, "")}/${platformPrefix}-update.json?${cacheBuster}`;
      try {
        const updateInfoResponse = await fetch(updateInfoUrl);
        if (updateInfoResponse.ok) {
          const responseText = await updateInfoResponse.text();
          try {
            updateInfo = JSON.parse(responseText);
          } catch {
            emitStatus("error", "Invalid update.json: failed to parse JSON", {
              url: updateInfoUrl
            });
            return {
              version: "",
              hash: "",
              updateAvailable: false,
              updateReady: false,
              error: `Invalid update.json: failed to parse JSON`
            };
          }
          if (!updateInfo.hash) {
            emitStatus("error", "Invalid update.json: missing hash", {
              url: updateInfoUrl
            });
            return {
              version: "",
              hash: "",
              updateAvailable: false,
              updateReady: false,
              error: `Invalid update.json: missing hash`
            };
          }
          if (updateInfo.hash !== localInfo2.hash) {
            updateInfo.updateAvailable = true;
            emitStatus("update-available", `Update available: ${localInfo2.hash.slice(0, 8)} \u2192 ${updateInfo.hash.slice(0, 8)}`, {
              currentHash: localInfo2.hash,
              latestHash: updateInfo.hash
            });
          } else {
            emitStatus("no-update", "Already on latest version", {
              currentHash: localInfo2.hash
            });
          }
        } else {
          emitStatus("error", `Failed to fetch update info (HTTP ${updateInfoResponse.status})`, { url: updateInfoUrl });
          return {
            version: "",
            hash: "",
            updateAvailable: false,
            updateReady: false,
            error: `Failed to fetch update info from ${updateInfoUrl}`
          };
        }
      } catch (error) {
        return {
          version: "",
          hash: "",
          updateAvailable: false,
          updateReady: false,
          error: `Failed to fetch update info from ${updateInfoUrl}`
        };
      }
      return updateInfo;
    },
    downloadUpdate: async () => {
      emitStatus("download-starting", "Starting update download...");
      const appDataFolder = await Updater.appDataFolder();
      await Updater.channelBucketUrl();
      const appFileName = localInfo.name;
      let currentHash = (await Updater.getLocallocalInfo()).hash;
      let latestHash = (await Updater.checkForUpdate()).hash;
      const extractionFolder = join2(appDataFolder, "self-extraction");
      if (!await Bun.file(extractionFolder).exists()) {
        mkdirSync(extractionFolder, { recursive: true });
      }
      let currentTarPath = join2(extractionFolder, `${currentHash}.tar`);
      const latestTarPath = join2(extractionFolder, `${latestHash}.tar`);
      const seenHashes = [];
      let patchesApplied = 0;
      let usedPatchPath = false;
      if (!await Bun.file(latestTarPath).exists()) {
        emitStatus("checking-local-tar", `Checking for local tar file: ${currentHash.slice(0, 8)}`, { currentHash });
        while (currentHash !== latestHash) {
          seenHashes.push(currentHash);
          const currentTar = Bun.file(currentTarPath);
          if (!await currentTar.exists()) {
            emitStatus("local-tar-missing", `Local tar not found for ${currentHash.slice(0, 8)}, will download full bundle`, { currentHash });
            break;
          }
          emitStatus("local-tar-found", `Found local tar for ${currentHash.slice(0, 8)}`, { currentHash });
          const platformPrefix = getPlatformPrefix(localInfo.channel, OS, ARCH);
          const patchUrl = `${localInfo.baseUrl.replace(/\/+$/, "")}/${platformPrefix}-${currentHash}.patch`;
          emitStatus("fetching-patch", `Checking for patch: ${currentHash.slice(0, 8)}`, { currentHash, url: patchUrl });
          const patchResponse = await fetch(patchUrl);
          if (!patchResponse.ok) {
            emitStatus("patch-not-found", `No patch available for ${currentHash.slice(0, 8)}, will download full bundle`, { currentHash });
            break;
          }
          emitStatus("patch-found", `Patch found for ${currentHash.slice(0, 8)}`, { currentHash });
          emitStatus("downloading-patch", `Downloading patch for ${currentHash.slice(0, 8)}...`, { currentHash });
          const patchFilePath = join2(appDataFolder, "self-extraction", `${currentHash}.patch`);
          await Bun.write(patchFilePath, await patchResponse.arrayBuffer());
          const tmpPatchedTarFilePath = join2(appDataFolder, "self-extraction", `from-${currentHash}.tar`);
          const bunBinDir = dirname(process.execPath);
          const bspatchBinName = OS === "win" ? "bspatch.exe" : "bspatch";
          const bspatchPath = join2(bunBinDir, bspatchBinName);
          emitStatus("applying-patch", `Applying patch ${patchesApplied + 1} for ${currentHash.slice(0, 8)}...`, {
            currentHash,
            patchNumber: patchesApplied + 1
          });
          if (!statSync(bspatchPath, { throwIfNoEntry: false })) {
            emitStatus("patch-failed", `bspatch binary not found at ${bspatchPath}`, {
              currentHash,
              errorMessage: `bspatch not found: ${bspatchPath}`
            });
            console.error("bspatch not found:", bspatchPath);
            break;
          }
          if (!statSync(currentTarPath, { throwIfNoEntry: false })) {
            emitStatus("patch-failed", `Old tar not found at ${currentTarPath}`, {
              currentHash,
              errorMessage: `old tar not found: ${currentTarPath}`
            });
            console.error("old tar not found:", currentTarPath);
            break;
          }
          if (!statSync(patchFilePath, { throwIfNoEntry: false })) {
            emitStatus("patch-failed", `Patch file not found at ${patchFilePath}`, {
              currentHash,
              errorMessage: `patch not found: ${patchFilePath}`
            });
            console.error("patch file not found:", patchFilePath);
            break;
          }
          try {
            const patchResult = Bun.spawnSync([
              bspatchPath,
              currentTarPath,
              tmpPatchedTarFilePath,
              patchFilePath
            ]);
            if (patchResult.exitCode !== 0 || patchResult.success === false) {
              const stderr = patchResult.stderr ? patchResult.stderr.toString() : "";
              const stdout = patchResult.stdout ? patchResult.stdout.toString() : "";
              if (updateInfo) {
                updateInfo.error = stderr || `bspatch failed with exit code ${patchResult.exitCode}`;
              }
              emitStatus("patch-failed", `Patch application failed: ${stderr || `exit code ${patchResult.exitCode}`}`, {
                currentHash,
                errorMessage: stderr || `exit code ${patchResult.exitCode}`
              });
              console.error("bspatch failed", {
                exitCode: patchResult.exitCode,
                stdout,
                stderr,
                bspatchPath,
                oldTar: currentTarPath,
                newTar: tmpPatchedTarFilePath,
                patch: patchFilePath
              });
              break;
            }
          } catch (error) {
            emitStatus("patch-failed", `Patch threw exception: ${error.message}`, {
              currentHash,
              errorMessage: error.message
            });
            console.error("bspatch threw", error, { bspatchPath });
            break;
          }
          patchesApplied++;
          emitStatus("patch-applied", `Patch ${patchesApplied} applied successfully`, {
            currentHash,
            patchNumber: patchesApplied
          });
          emitStatus("extracting-version", "Extracting version info from patched tar...", { currentHash });
          let hashFilePath = "";
          const resourcesDir = "Resources";
          const patchedTarBytes = await Bun.file(tmpPatchedTarFilePath).arrayBuffer();
          const patchedArchive = new Bun.Archive(patchedTarBytes);
          const patchedFiles = await patchedArchive.files();
          for (const [filePath] of patchedFiles) {
            if (filePath.endsWith(`${resourcesDir}/version.json`) || filePath.endsWith("metadata.json")) {
              hashFilePath = filePath;
              break;
            }
          }
          if (!hashFilePath) {
            emitStatus("error", "Could not find version/metadata file in patched tar", { currentHash });
            console.error("Neither Resources/version.json nor metadata.json found in patched tar:", tmpPatchedTarFilePath);
            break;
          }
          const hashFile = patchedFiles.get(hashFilePath);
          const hashFileJson = JSON.parse(await hashFile.text());
          const nextHash = hashFileJson.hash;
          if (seenHashes.includes(nextHash)) {
            emitStatus("error", "Cyclical update detected, falling back to full download", { currentHash: nextHash });
            console.log("Warning: cyclical update detected");
            break;
          }
          seenHashes.push(nextHash);
          if (!nextHash) {
            emitStatus("error", "Could not determine next hash from patched tar", { currentHash });
            break;
          }
          const updatedTarPath = join2(appDataFolder, "self-extraction", `${nextHash}.tar`);
          renameSync(tmpPatchedTarFilePath, updatedTarPath);
          unlinkSync(currentTarPath);
          unlinkSync(patchFilePath);
          currentHash = nextHash;
          currentTarPath = join2(appDataFolder, "self-extraction", `${currentHash}.tar`);
          emitStatus("patch-applied", `Patched to ${nextHash.slice(0, 8)}, checking for more patches...`, {
            currentHash: nextHash,
            toHash: latestHash,
            totalPatchesApplied: patchesApplied
          });
        }
        if (currentHash === latestHash && patchesApplied > 0) {
          usedPatchPath = true;
          emitStatus("patch-chain-complete", `Patch chain complete! Applied ${patchesApplied} patches`, {
            totalPatchesApplied: patchesApplied,
            currentHash: latestHash,
            usedPatchPath: true
          });
        }
        if (currentHash !== latestHash) {
          emitStatus("downloading-full-bundle", "Downloading full update bundle...", {
            currentHash,
            latestHash,
            usedPatchPath: false
          });
          const cacheBuster = Math.random().toString(36).substring(7);
          const platformPrefix = getPlatformPrefix(localInfo.channel, OS, ARCH);
          const tarballName = getTarballFileName(appFileName, OS);
          const urlToLatestTarball = `${localInfo.baseUrl.replace(/\/+$/, "")}/${platformPrefix}-${tarballName}`;
          const prevVersionCompressedTarballPath = join2(appDataFolder, "self-extraction", "latest.tar.zst");
          emitStatus("download-progress", `Fetching ${tarballName}...`, {
            url: urlToLatestTarball
          });
          const response = await fetch(urlToLatestTarball + `?${cacheBuster}`);
          if (response.ok && response.body) {
            const contentLength = response.headers.get("content-length");
            const totalBytes = contentLength ? parseInt(contentLength, 10) : undefined;
            let bytesDownloaded = 0;
            const reader = response.body.getReader();
            const writer = Bun.file(prevVersionCompressedTarballPath).writer();
            while (true) {
              const { done, value } = await reader.read();
              if (done)
                break;
              await writer.write(value);
              bytesDownloaded += value.length;
              if (bytesDownloaded % 500000 < value.length) {
                emitStatus("download-progress", `Downloading: ${(bytesDownloaded / 1024 / 1024).toFixed(1)} MB`, {
                  bytesDownloaded,
                  totalBytes,
                  progress: totalBytes ? Math.round(bytesDownloaded / totalBytes * 100) : undefined
                });
              }
            }
            await writer.flush();
            writer.end();
            emitStatus("download-progress", `Download complete: ${(bytesDownloaded / 1024 / 1024).toFixed(1)} MB`, {
              bytesDownloaded,
              totalBytes,
              progress: 100
            });
          } else {
            emitStatus("error", `Failed to download: ${urlToLatestTarball}`, {
              url: urlToLatestTarball
            });
            console.log("latest version not found at: ", urlToLatestTarball);
          }
          emitStatus("decompressing", "Decompressing update bundle...");
          const bunBinDir = dirname(process.execPath);
          const zstdBinName = OS === "win" ? "zig-zstd.exe" : "zig-zstd";
          const zstdPath = join2(bunBinDir, zstdBinName);
          if (!statSync(zstdPath, { throwIfNoEntry: false })) {
            updateInfo.error = `zig-zstd not found: ${zstdPath}`;
            emitStatus("error", updateInfo.error, { zstdPath });
            console.error("zig-zstd not found:", zstdPath);
          } else {
            const decompressResult = Bun.spawnSync([
              zstdPath,
              "decompress",
              "-i",
              prevVersionCompressedTarballPath,
              "-o",
              latestTarPath,
              "--no-timing"
            ], {
              cwd: extractionFolder,
              stdout: "inherit",
              stderr: "inherit"
            });
            if (!decompressResult.success) {
              updateInfo.error = `zig-zstd failed with exit code ${decompressResult.exitCode}`;
              emitStatus("error", updateInfo.error, {
                zstdPath,
                exitCode: decompressResult.exitCode
              });
              console.error("zig-zstd failed", {
                exitCode: decompressResult.exitCode,
                zstdPath
              });
            } else {
              emitStatus("decompressing", "Decompression complete");
            }
          }
          unlinkSync(prevVersionCompressedTarballPath);
        }
      }
      if (await Bun.file(latestTarPath).exists()) {
        updateInfo.updateReady = true;
        emitStatus("download-complete", `Update ready to install (used ${usedPatchPath ? "patch" : "full download"} path)`, {
          latestHash,
          usedPatchPath,
          totalPatchesApplied: patchesApplied
        });
      } else {
        updateInfo.error = "Failed to download latest version";
        emitStatus("error", "Failed to download latest version", { latestHash });
      }
      cleanupExtractionFolder(extractionFolder, latestHash);
    },
    applyUpdate: async () => {
      if (updateInfo?.updateReady) {
        emitStatus("applying", "Starting update installation...");
        const appDataFolder = await Updater.appDataFolder();
        const extractionFolder = join2(appDataFolder, "self-extraction");
        if (!await Bun.file(extractionFolder).exists()) {
          mkdirSync(extractionFolder, { recursive: true });
        }
        let latestHash = (await Updater.checkForUpdate()).hash;
        const latestTarPath = join2(extractionFolder, `${latestHash}.tar`);
        let appBundleSubpath = "";
        if (await Bun.file(latestTarPath).exists()) {
          emitStatus("extracting", `Extracting update to ${latestHash.slice(0, 8)}...`, { latestHash });
          const extractionDir = OS === "win" ? join2(extractionFolder, `temp-${latestHash}`) : extractionFolder;
          if (OS === "win") {
            mkdirSync(extractionDir, { recursive: true });
          }
          const latestTarBytes = await Bun.file(latestTarPath).arrayBuffer();
          const latestArchive = new Bun.Archive(latestTarBytes);
          await latestArchive.extract(extractionDir);
          if (OS === "macos") {
            const extractedFiles = readdirSync(extractionDir);
            for (const file of extractedFiles) {
              if (file.endsWith(".app")) {
                appBundleSubpath = file + "/";
                break;
              }
            }
          } else {
            appBundleSubpath = "./";
          }
          console.log(`Tar extraction completed. Found appBundleSubpath: ${appBundleSubpath}`);
          if (!appBundleSubpath) {
            console.error("Failed to find app in tarball");
            return;
          }
          const extractedAppPath = resolve(join2(extractionDir, appBundleSubpath));
          let newAppBundlePath;
          if (OS === "linux") {
            const extractedFiles = readdirSync(extractionDir);
            const appBundleDir = extractedFiles.find((file) => {
              const filePath = join2(extractionDir, file);
              return statSync(filePath).isDirectory() && !file.endsWith(".tar");
            });
            if (!appBundleDir) {
              console.error("Could not find app bundle directory in extraction");
              return;
            }
            newAppBundlePath = join2(extractionDir, appBundleDir);
            const bundleStats = statSync(newAppBundlePath, { throwIfNoEntry: false });
            if (!bundleStats || !bundleStats.isDirectory()) {
              console.error(`App bundle directory not found at: ${newAppBundlePath}`);
              console.log("Contents of extraction directory:");
              try {
                const files = readdirSync(extractionDir);
                for (const file of files) {
                  console.log(`  - ${file}`);
                  const subPath = join2(extractionDir, file);
                  if (statSync(subPath).isDirectory()) {
                    const subFiles = readdirSync(subPath);
                    for (const subFile of subFiles) {
                      console.log(`    - ${subFile}`);
                    }
                  }
                }
              } catch (e) {
                console.log("Could not list directory contents:", e);
              }
              return;
            }
          } else if (OS === "win") {
            const appBundleName = getAppFileName(localInfo.name, localInfo.channel);
            newAppBundlePath = join2(extractionDir, appBundleName);
            if (!statSync(newAppBundlePath, { throwIfNoEntry: false })) {
              console.error(`Extracted app not found at: ${newAppBundlePath}`);
              console.log("Contents of extraction directory:");
              try {
                const files = readdirSync(extractionDir);
                for (const file of files) {
                  console.log(`  - ${file}`);
                }
              } catch (e) {
                console.log("Could not list directory contents:", e);
              }
              return;
            }
          } else {
            newAppBundlePath = extractedAppPath;
          }
          let runningAppBundlePath;
          const appDataFolder2 = await Updater.appDataFolder();
          if (OS === "macos") {
            runningAppBundlePath = resolve(dirname(process.execPath), "..", "..");
          } else if (OS === "linux" || OS === "win") {
            runningAppBundlePath = join2(appDataFolder2, "app");
          } else {
            throw new Error(`Unsupported platform: ${OS}`);
          }
          try {
            emitStatus("replacing-app", "Removing old version...");
            if (OS === "macos") {
              if (statSync(runningAppBundlePath, { throwIfNoEntry: false })) {
                rmdirSync(runningAppBundlePath, { recursive: true });
              }
              emitStatus("replacing-app", "Installing new version...");
              renameSync(newAppBundlePath, runningAppBundlePath);
              try {
                execSync(`xattr -r -d com.apple.quarantine "${runningAppBundlePath}"`, { stdio: "ignore" });
              } catch (e) {}
            } else if (OS === "linux") {
              const appBundleDir = join2(appDataFolder2, "app");
              if (statSync(appBundleDir, { throwIfNoEntry: false })) {
                rmdirSync(appBundleDir, { recursive: true });
              }
              renameSync(newAppBundlePath, appBundleDir);
              const launcherPath = join2(appBundleDir, "bin", "launcher");
              if (statSync(launcherPath, { throwIfNoEntry: false })) {
                execSync(`chmod +x "${launcherPath}"`);
              }
              const bunPath = join2(appBundleDir, "bin", "bun");
              if (statSync(bunPath, { throwIfNoEntry: false })) {
                execSync(`chmod +x "${bunPath}"`);
              }
            }
            if (OS !== "win") {
              cleanupExtractionFolder(extractionFolder, latestHash);
            }
            if (OS === "win") {
              const parentDir = dirname(runningAppBundlePath);
              const updateScriptPath = join2(parentDir, "update.bat");
              const launcherPath = join2(runningAppBundlePath, "bin", "launcher.exe");
              const runningAppWin = runningAppBundlePath.replace(/\//g, "\\");
              const newAppWin = newAppBundlePath.replace(/\//g, "\\");
              const extractionDirWin = extractionDir.replace(/\//g, "\\");
              const launcherPathWin = launcherPath.replace(/\//g, "\\");
              const updateScript = `@echo off
setlocal

:: Wait for the app to fully exit (check if launcher.exe is still running)
:waitloop
tasklist /FI "IMAGENAME eq launcher.exe" 2>NUL | find /I /N "launcher.exe">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >nul
    goto waitloop
)

:: Small extra delay to ensure all file handles are released
timeout /t 2 /nobreak >nul

:: Remove current app folder
if exist "${runningAppWin}" (
    rmdir /s /q "${runningAppWin}"
)

:: Move new app to current location
move "${newAppWin}" "${runningAppWin}"

:: Clean up extraction directory
rmdir /s /q "${extractionDirWin}" 2>nul

:: Launch the new app
start "" "${launcherPathWin}"

:: Clean up scheduled tasks starting with ElectrobunUpdate_
for /f "tokens=1" %%t in ('schtasks /query /fo list ^| findstr /i "ElectrobunUpdate_"') do (
    schtasks /delete /tn "%%t" /f >nul 2>&1
)

:: Delete this update script after a short delay
ping -n 2 127.0.0.1 >nul
del "%~f0"
`;
              await Bun.write(updateScriptPath, updateScript);
              const scriptPathWin = updateScriptPath.replace(/\//g, "\\");
              const taskName = `ElectrobunUpdate_${Date.now()}`;
              execSync(`schtasks /create /tn "${taskName}" /tr "cmd /c \\"${scriptPathWin}\\"" /sc once /st 00:00 /f`, { stdio: "ignore" });
              execSync(`schtasks /run /tn "${taskName}"`, { stdio: "ignore" });
              quit();
            }
          } catch (error) {
            emitStatus("error", `Failed to replace app: ${error.message}`, {
              errorMessage: error.message
            });
            console.error("Failed to replace app with new version", error);
            return;
          }
          emitStatus("launching-new-version", "Launching updated version...");
          if (OS === "macos") {
            const pid = process.pid;
            Bun.spawn([
              "sh",
              "-c",
              `while kill -0 ${pid} 2>/dev/null; do sleep 0.5; done; sleep 1; open "${runningAppBundlePath}"`
            ], {
              detached: true,
              stdio: ["ignore", "ignore", "ignore"]
            });
          } else if (OS === "linux") {
            const launcherPath = join2(runningAppBundlePath, "bin", "launcher");
            Bun.spawn(["sh", "-c", `"${launcherPath}" &`], {
              detached: true
            });
          }
          emitStatus("complete", "Update complete, restarting application...");
          quit();
        }
      }
    },
    channelBucketUrl: async () => {
      await Updater.getLocallocalInfo();
      return localInfo.baseUrl;
    },
    appDataFolder: async () => {
      await Updater.getLocallocalInfo();
      const appDataFolder = join2(getAppDataDir2(), localInfo.identifier, localInfo.channel);
      return appDataFolder;
    },
    localInfo: {
      version: async () => {
        return (await Updater.getLocallocalInfo()).version;
      },
      hash: async () => {
        return (await Updater.getLocallocalInfo()).hash;
      },
      channel: async () => {
        return (await Updater.getLocallocalInfo()).channel;
      },
      baseUrl: async () => {
        return (await Updater.getLocallocalInfo()).baseUrl;
      }
    },
    getLocallocalInfo: async () => {
      if (localInfo) {
        return localInfo;
      }
      try {
        const resourcesDir = "Resources";
        localInfo = await Bun.file(`../${resourcesDir}/version.json`).json();
        return localInfo;
      } catch (error) {
        console.error("Failed to read version.json", error);
        throw error;
      }
    }
  };
});

// node_modules/electrobun/dist/api/bun/core/BuildConfig.ts
var buildConfig = null, BuildConfig;
var init_BuildConfig = __esm(() => {
  BuildConfig = {
    get: async () => {
      if (buildConfig) {
        return buildConfig;
      }
      try {
        const resourcesDir = "Resources";
        buildConfig = await Bun.file(`../${resourcesDir}/build.json`).json();
        return buildConfig;
      } catch (error) {
        buildConfig = {
          defaultRenderer: "native",
          availableRenderers: ["native"]
        };
        return buildConfig;
      }
    },
    getCached: () => buildConfig
  };
});

// node_modules/electrobun/dist/api/bun/core/Socket.ts
import { createCipheriv, createDecipheriv, randomBytes } from "crypto";
function base64ToUint8Array(base64) {
  {
    return new Uint8Array(atob(base64).split("").map((char) => char.charCodeAt(0)));
  }
}
function encrypt(secretKey, text) {
  const iv = new Uint8Array(randomBytes(12));
  const cipher = createCipheriv("aes-256-gcm", secretKey, iv);
  const encrypted = Buffer.concat([
    new Uint8Array(cipher.update(text, "utf8")),
    new Uint8Array(cipher.final())
  ]).toString("base64");
  const tag = cipher.getAuthTag().toString("base64");
  return { encrypted, iv: Buffer.from(iv).toString("base64"), tag };
}
function decrypt(secretKey, encryptedData, iv, tag) {
  const decipher = createDecipheriv("aes-256-gcm", secretKey, iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([
    new Uint8Array(decipher.update(encryptedData)),
    new Uint8Array(decipher.final())
  ]);
  return decrypted.toString("utf8");
}
var socketMap, startRPCServer = () => {
  const startPort = 50000;
  const endPort = 65535;
  const payloadLimit = 1024 * 1024 * 500;
  let port = startPort;
  let server = null;
  while (port <= endPort) {
    try {
      server = Bun.serve({
        port,
        fetch(req, server2) {
          const url = new URL(req.url);
          if (url.pathname === "/socket") {
            const webviewIdString = url.searchParams.get("webviewId");
            if (!webviewIdString) {
              return new Response("Missing webviewId", { status: 400 });
            }
            const webviewId = parseInt(webviewIdString, 10);
            const success = server2.upgrade(req, { data: { webviewId } });
            return success ? undefined : new Response("Upgrade failed", { status: 500 });
          }
          console.log("unhandled RPC Server request", req.url);
        },
        websocket: {
          idleTimeout: 960,
          maxPayloadLength: payloadLimit,
          backpressureLimit: payloadLimit * 2,
          open(ws) {
            if (!ws?.data) {
              return;
            }
            const { webviewId } = ws.data;
            if (!socketMap[webviewId]) {
              socketMap[webviewId] = { socket: ws, queue: [] };
            } else {
              socketMap[webviewId].socket = ws;
            }
          },
          close(ws, _code, _reason) {
            if (!ws?.data) {
              return;
            }
            const { webviewId } = ws.data;
            if (socketMap[webviewId]) {
              socketMap[webviewId].socket = null;
            }
          },
          message(ws, message) {
            if (!ws?.data) {
              return;
            }
            const { webviewId } = ws.data;
            const browserView = BrowserView.getById(webviewId);
            if (!browserView) {
              return;
            }
            if (browserView.rpcHandler) {
              if (typeof message === "string") {
                try {
                  const encryptedPacket = JSON.parse(message);
                  const decrypted = decrypt(browserView.secretKey, base64ToUint8Array(encryptedPacket.encryptedData), base64ToUint8Array(encryptedPacket.iv), base64ToUint8Array(encryptedPacket.tag));
                  browserView.rpcHandler(JSON.parse(decrypted));
                } catch (error) {
                  console.log("Error handling message:", error);
                }
              } else if (message instanceof ArrayBuffer) {
                console.log("TODO: Received ArrayBuffer message:", message);
              }
            }
          }
        }
      });
      break;
    } catch (error) {
      if (error.code === "EADDRINUSE") {
        console.log(`Port ${port} in use, trying next port...`);
        port++;
      } else {
        throw error;
      }
    }
  }
  return { rpcServer: server, rpcPort: port };
}, rpcServer, rpcPort, sendMessageToWebviewViaSocket = (webviewId, message) => {
  const rpc = socketMap[webviewId];
  const browserView = BrowserView.getById(webviewId);
  if (!browserView)
    return false;
  if (rpc?.socket?.readyState === WebSocket.OPEN) {
    try {
      const unencryptedString = JSON.stringify(message);
      const encrypted = encrypt(browserView.secretKey, unencryptedString);
      const encryptedPacket = {
        encryptedData: encrypted.encrypted,
        iv: encrypted.iv,
        tag: encrypted.tag
      };
      const encryptedPacketString = JSON.stringify(encryptedPacket);
      rpc.socket.send(encryptedPacketString);
      return true;
    } catch (error) {
      console.error("Error sending message to webview via socket:", error);
    }
  }
  return false;
};
var init_Socket = __esm(async () => {
  await init_BrowserView();
  socketMap = {};
  ({ rpcServer, rpcPort } = startRPCServer());
  console.log("Server started at", rpcServer?.url.origin);
});

// node_modules/electrobun/dist/api/bun/core/BrowserView.ts
import { randomBytes as randomBytes2 } from "crypto";

class BrowserView {
  id = nextWebviewId++;
  ptr;
  hostWebviewId;
  windowId;
  renderer;
  url = null;
  html = null;
  preload = null;
  partition = null;
  autoResize = true;
  frame = {
    x: 0,
    y: 0,
    width: 800,
    height: 600
  };
  pipePrefix;
  inStream;
  outStream;
  secretKey;
  rpc;
  rpcHandler;
  navigationRules = null;
  sandbox = false;
  startTransparent = false;
  startPassthrough = false;
  constructor(options = defaultOptions) {
    this.url = options.url || defaultOptions.url || null;
    this.html = options.html || defaultOptions.html || null;
    this.preload = options.preload || defaultOptions.preload || null;
    this.frame = {
      x: options.frame?.x ?? defaultOptions.frame.x,
      y: options.frame?.y ?? defaultOptions.frame.y,
      width: options.frame?.width ?? defaultOptions.frame.width,
      height: options.frame?.height ?? defaultOptions.frame.height
    };
    this.rpc = options.rpc;
    this.secretKey = new Uint8Array(randomBytes2(32));
    this.partition = options.partition || null;
    this.pipePrefix = `/private/tmp/electrobun_ipc_pipe_${hash}_${randomId}_${this.id}`;
    this.hostWebviewId = options.hostWebviewId;
    this.windowId = options.windowId ?? 0;
    this.autoResize = options.autoResize === false ? false : true;
    this.navigationRules = options.navigationRules || null;
    this.renderer = options.renderer ?? defaultOptions.renderer ?? "native";
    this.sandbox = options.sandbox ?? false;
    this.startTransparent = options.startTransparent ?? false;
    this.startPassthrough = options.startPassthrough ?? false;
    BrowserViewMap[this.id] = this;
    this.ptr = this.init();
    if (this.html) {
      console.log(`DEBUG: BrowserView constructor triggering loadHTML for webview ${this.id}`);
      setTimeout(() => {
        console.log(`DEBUG: BrowserView delayed loadHTML for webview ${this.id}`);
        this.loadHTML(this.html);
      }, 100);
    } else {
      console.log(`DEBUG: BrowserView constructor - no HTML provided for webview ${this.id}`);
    }
  }
  init() {
    this.createStreams();
    return ffi.request.createWebview({
      id: this.id,
      windowId: this.windowId,
      renderer: this.renderer,
      rpcPort,
      secretKey: this.secretKey.toString(),
      hostWebviewId: this.hostWebviewId || null,
      pipePrefix: this.pipePrefix,
      partition: this.partition,
      url: this.html ? null : this.url,
      html: this.html,
      preload: this.preload,
      frame: {
        width: this.frame.width,
        height: this.frame.height,
        x: this.frame.x,
        y: this.frame.y
      },
      autoResize: this.autoResize,
      navigationRules: this.navigationRules,
      sandbox: this.sandbox,
      startTransparent: this.startTransparent,
      startPassthrough: this.startPassthrough
    });
  }
  createStreams() {
    if (!this.rpc) {
      this.rpc = BrowserView.defineRPC({
        handlers: { requests: {}, messages: {} }
      });
    }
    this.rpc.setTransport(this.createTransport());
  }
  sendMessageToWebviewViaExecute(jsonMessage) {
    const stringifiedMessage = typeof jsonMessage === "string" ? jsonMessage : JSON.stringify(jsonMessage);
    const wrappedMessage = `window.__electrobun.receiveMessageFromBun(${stringifiedMessage})`;
    this.executeJavascript(wrappedMessage);
  }
  sendInternalMessageViaExecute(jsonMessage) {
    const stringifiedMessage = typeof jsonMessage === "string" ? jsonMessage : JSON.stringify(jsonMessage);
    const wrappedMessage = `window.__electrobun.receiveInternalMessageFromBun(${stringifiedMessage})`;
    this.executeJavascript(wrappedMessage);
  }
  executeJavascript(js) {
    ffi.request.evaluateJavascriptWithNoCompletion({ id: this.id, js });
  }
  loadURL(url) {
    console.log(`DEBUG: loadURL called for webview ${this.id}: ${url}`);
    this.url = url;
    native.symbols.loadURLInWebView(this.ptr, toCString(this.url));
  }
  loadHTML(html) {
    this.html = html;
    console.log(`DEBUG: Setting HTML content for webview ${this.id}:`, html.substring(0, 50) + "...");
    if (this.renderer === "cef") {
      native.symbols.setWebviewHTMLContent(this.id, toCString(html));
      this.loadURL("views://internal/index.html");
    } else {
      native.symbols.loadHTMLInWebView(this.ptr, toCString(html));
    }
  }
  setNavigationRules(rules) {
    this.navigationRules = JSON.stringify(rules);
    const rulesJson = JSON.stringify(rules);
    native.symbols.setWebviewNavigationRules(this.ptr, toCString(rulesJson));
  }
  findInPage(searchText, options) {
    const forward = options?.forward ?? true;
    const matchCase = options?.matchCase ?? false;
    native.symbols.webviewFindInPage(this.ptr, toCString(searchText), forward, matchCase);
  }
  stopFindInPage() {
    native.symbols.webviewStopFind(this.ptr);
  }
  openDevTools() {
    native.symbols.webviewOpenDevTools(this.ptr);
  }
  closeDevTools() {
    native.symbols.webviewCloseDevTools(this.ptr);
  }
  toggleDevTools() {
    native.symbols.webviewToggleDevTools(this.ptr);
  }
  on(name, handler) {
    const specificName = `${name}-${this.id}`;
    eventEmitter_default.on(specificName, handler);
  }
  createTransport = () => {
    const that = this;
    return {
      send(message) {
        const sentOverSocket = sendMessageToWebviewViaSocket(that.id, message);
        if (!sentOverSocket) {
          try {
            const messageString = JSON.stringify(message);
            that.sendMessageToWebviewViaExecute(messageString);
          } catch (error) {
            console.error("bun: failed to serialize message to webview", error);
          }
        }
      },
      registerHandler(handler) {
        that.rpcHandler = handler;
      }
    };
  };
  remove() {
    native.symbols.webviewRemove(this.ptr);
    delete BrowserViewMap[this.id];
  }
  static getById(id) {
    return BrowserViewMap[id];
  }
  static getAll() {
    return Object.values(BrowserViewMap);
  }
  static defineRPC(config) {
    return defineElectrobunRPC("bun", config);
  }
}
var BrowserViewMap, nextWebviewId = 1, hash, buildConfig2, defaultOptions, randomId;
var init_BrowserView = __esm(async () => {
  init_eventEmitter();
  init_BuildConfig();
  await __promiseAll([
    init_native(),
    init_Updater(),
    init_Socket()
  ]);
  BrowserViewMap = {};
  hash = await Updater.localInfo.hash();
  buildConfig2 = await BuildConfig.get();
  defaultOptions = {
    url: null,
    html: null,
    preload: null,
    renderer: buildConfig2.defaultRenderer,
    frame: {
      x: 0,
      y: 0,
      width: 800,
      height: 600
    }
  };
  randomId = Math.random().toString(36).substring(7);
});

// node_modules/electrobun/dist/api/bun/core/Paths.ts
import { resolve as resolve2 } from "path";
var RESOURCES_FOLDER, VIEWS_FOLDER;
var init_Paths = __esm(() => {
  RESOURCES_FOLDER = resolve2("../Resources/");
  VIEWS_FOLDER = resolve2(RESOURCES_FOLDER, "app/views");
});

// node_modules/electrobun/dist/api/bun/core/Tray.ts
import { join as join3 } from "path";

class Tray {
  id = nextTrayId++;
  ptr = null;
  constructor({
    title = "",
    image = "",
    template = true,
    width = 16,
    height = 16
  } = {}) {
    try {
      this.ptr = ffi.request.createTray({
        id: this.id,
        title,
        image: this.resolveImagePath(image),
        template,
        width,
        height
      });
    } catch (error) {
      console.warn("Tray creation failed:", error);
      console.warn("System tray functionality may not be available on this platform");
      this.ptr = null;
    }
    TrayMap[this.id] = this;
  }
  resolveImagePath(imgPath) {
    if (imgPath.startsWith("views://")) {
      return join3(VIEWS_FOLDER, imgPath.replace("views://", ""));
    } else {
      return imgPath;
    }
  }
  setTitle(title) {
    if (!this.ptr)
      return;
    ffi.request.setTrayTitle({ id: this.id, title });
  }
  setImage(imgPath) {
    if (!this.ptr)
      return;
    ffi.request.setTrayImage({
      id: this.id,
      image: this.resolveImagePath(imgPath)
    });
  }
  setMenu(menu) {
    if (!this.ptr)
      return;
    const menuWithDefaults = menuConfigWithDefaults(menu);
    ffi.request.setTrayMenu({
      id: this.id,
      menuConfig: JSON.stringify(menuWithDefaults)
    });
  }
  on(name, handler) {
    const specificName = `${name}-${this.id}`;
    eventEmitter_default.on(specificName, handler);
  }
  remove() {
    console.log("Tray.remove() called for id:", this.id);
    if (this.ptr) {
      ffi.request.removeTray({ id: this.id });
    }
    delete TrayMap[this.id];
    console.log("Tray removed from TrayMap");
  }
  static getById(id) {
    return TrayMap[id];
  }
  static getAll() {
    return Object.values(TrayMap);
  }
  static removeById(id) {
    const tray = TrayMap[id];
    if (tray) {
      tray.remove();
    }
  }
}
var nextTrayId = 1, TrayMap, menuConfigWithDefaults = (menu) => {
  return menu.map((item) => {
    if (item.type === "divider" || item.type === "separator") {
      return { type: "divider" };
    } else {
      const menuItem = item;
      const actionWithDataId = ffi.internal.serializeMenuAction(menuItem.action || "", menuItem.data);
      return {
        label: menuItem.label || "",
        type: menuItem.type || "normal",
        action: actionWithDataId,
        enabled: menuItem.enabled === false ? false : true,
        checked: Boolean(menuItem.checked),
        hidden: Boolean(menuItem.hidden),
        tooltip: menuItem.tooltip || undefined,
        ...menuItem.submenu ? { submenu: menuConfigWithDefaults(menuItem.submenu) } : {}
      };
    }
  });
};
var init_Tray = __esm(async () => {
  init_eventEmitter();
  init_Paths();
  await init_native();
  TrayMap = {};
});

// node_modules/electrobun/dist/api/bun/preload/.generated/compiled.ts
var preloadScript = `(() => {
  // src/bun/preload/encryption.ts
  function base64ToUint8Array(base64) {
    return new Uint8Array(atob(base64).split("").map((char) => char.charCodeAt(0)));
  }
  function uint8ArrayToBase64(uint8Array) {
    let binary = "";
    for (let i = 0;i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
  }
  async function generateKeyFromBytes(rawKey) {
    return await window.crypto.subtle.importKey("raw", rawKey, { name: "AES-GCM" }, true, ["encrypt", "decrypt"]);
  }
  async function initEncryption() {
    const secretKey = await generateKeyFromBytes(new Uint8Array(window.__electrobunSecretKeyBytes));
    const encryptString = async (plaintext) => {
      const encoder = new TextEncoder;
      const encodedText = encoder.encode(plaintext);
      const iv = window.crypto.getRandomValues(new Uint8Array(12));
      const encryptedBuffer = await window.crypto.subtle.encrypt({ name: "AES-GCM", iv }, secretKey, encodedText);
      const encryptedData = new Uint8Array(encryptedBuffer.slice(0, -16));
      const tag = new Uint8Array(encryptedBuffer.slice(-16));
      return {
        encryptedData: uint8ArrayToBase64(encryptedData),
        iv: uint8ArrayToBase64(iv),
        tag: uint8ArrayToBase64(tag)
      };
    };
    const decryptString = async (encryptedDataB64, ivB64, tagB64) => {
      const encryptedData = base64ToUint8Array(encryptedDataB64);
      const iv = base64ToUint8Array(ivB64);
      const tag = base64ToUint8Array(tagB64);
      const combinedData = new Uint8Array(encryptedData.length + tag.length);
      combinedData.set(encryptedData);
      combinedData.set(tag, encryptedData.length);
      const decryptedBuffer = await window.crypto.subtle.decrypt({ name: "AES-GCM", iv }, secretKey, combinedData);
      const decoder = new TextDecoder;
      return decoder.decode(decryptedBuffer);
    };
    window.__electrobun_encrypt = encryptString;
    window.__electrobun_decrypt = decryptString;
  }

  // src/bun/preload/internalRpc.ts
  var pendingRequests = {};
  var requestId = 0;
  var isProcessingQueue = false;
  var sendQueue = [];
  function processQueue() {
    if (isProcessingQueue) {
      setTimeout(processQueue);
      return;
    }
    if (sendQueue.length === 0)
      return;
    isProcessingQueue = true;
    const batch = JSON.stringify(sendQueue);
    sendQueue.length = 0;
    window.__electrobunInternalBridge?.postMessage(batch);
    setTimeout(() => {
      isProcessingQueue = false;
    }, 2);
  }
  function send(type, payload) {
    sendQueue.push(JSON.stringify({ type: "message", id: type, payload }));
    processQueue();
  }
  function request(type, payload) {
    return new Promise((resolve, reject) => {
      const id = \`req_\${++requestId}_\${Date.now()}\`;
      pendingRequests[id] = { resolve, reject };
      sendQueue.push(JSON.stringify({
        type: "request",
        method: type,
        id,
        params: payload,
        hostWebviewId: window.__electrobunWebviewId
      }));
      processQueue();
      setTimeout(() => {
        if (pendingRequests[id]) {
          delete pendingRequests[id];
          reject(new Error(\`Request timeout: \${type}\`));
        }
      }, 1e4);
    });
  }
  function handleResponse(msg) {
    if (msg && msg.type === "response" && msg.id) {
      const pending = pendingRequests[msg.id];
      if (pending) {
        delete pendingRequests[msg.id];
        if (msg.success)
          pending.resolve(msg.payload);
        else
          pending.reject(msg.payload);
      }
    }
  }

  // src/bun/preload/dragRegions.ts
  function isAppRegionDrag(e) {
    const target = e.target;
    if (!target || !target.closest)
      return false;
    const draggableByStyle = target.closest('[style*="app-region"][style*="drag"]');
    const draggableByClass = target.closest(".electrobun-webkit-app-region-drag");
    return !!(draggableByStyle || draggableByClass);
  }
  function initDragRegions() {
    document.addEventListener("mousedown", (e) => {
      if (isAppRegionDrag(e)) {
        send("startWindowMove", { id: window.__electrobunWindowId });
      }
    });
    document.addEventListener("mouseup", (e) => {
      if (isAppRegionDrag(e)) {
        send("stopWindowMove", { id: window.__electrobunWindowId });
      }
    });
  }

  // src/bun/preload/webviewTag.ts
  var webviewRegistry = {};

  class ElectrobunWebviewTag extends HTMLElement {
    webviewId = null;
    maskSelectors = new Set;
    lastRect = { x: 0, y: 0, width: 0, height: 0 };
    resizeObserver = null;
    positionCheckLoop = null;
    transparent = false;
    passthroughEnabled = false;
    hidden = false;
    sandboxed = false;
    _eventListeners = {};
    constructor() {
      super();
    }
    connectedCallback() {
      requestAnimationFrame(() => this.initWebview());
    }
    disconnectedCallback() {
      if (this.webviewId !== null) {
        send("webviewTagRemove", { id: this.webviewId });
        delete webviewRegistry[this.webviewId];
      }
      if (this.resizeObserver)
        this.resizeObserver.disconnect();
      if (this.positionCheckLoop)
        clearInterval(this.positionCheckLoop);
    }
    async initWebview() {
      const rect = this.getBoundingClientRect();
      this.lastRect = {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height
      };
      const url = this.getAttribute("src");
      const html = this.getAttribute("html");
      const preload = this.getAttribute("preload");
      const partition = this.getAttribute("partition");
      const renderer = this.getAttribute("renderer") || "native";
      const masks = this.getAttribute("masks");
      const sandbox = this.hasAttribute("sandbox");
      this.sandboxed = sandbox;
      const transparent = this.hasAttribute("transparent");
      const passthrough = this.hasAttribute("passthrough");
      this.transparent = transparent;
      this.passthroughEnabled = passthrough;
      if (transparent)
        this.style.opacity = "0";
      if (passthrough)
        this.style.pointerEvents = "none";
      if (masks) {
        masks.split(",").forEach((s) => this.maskSelectors.add(s.trim()));
      }
      try {
        const webviewId = await request("webviewTagInit", {
          hostWebviewId: window.__electrobunWebviewId,
          windowId: window.__electrobunWindowId,
          renderer,
          url,
          html,
          preload,
          partition,
          frame: {
            width: rect.width,
            height: rect.height,
            x: rect.x,
            y: rect.y
          },
          navigationRules: null,
          sandbox,
          transparent,
          passthrough
        });
        this.webviewId = webviewId;
        this.id = \`electrobun-webview-\${webviewId}\`;
        webviewRegistry[webviewId] = this;
        this.setupObservers();
        this.syncDimensions(true);
        requestAnimationFrame(() => {
          Object.values(webviewRegistry).forEach((webview) => {
            if (webview !== this && webview.webviewId !== null) {
              webview.syncDimensions(true);
            }
          });
        });
      } catch (err) {
        console.error("Failed to init webview:", err);
      }
    }
    setupObservers() {
      this.resizeObserver = new ResizeObserver(() => this.syncDimensions());
      this.resizeObserver.observe(this);
      this.positionCheckLoop = setInterval(() => this.syncDimensions(), 100);
    }
    syncDimensions(force = false) {
      if (this.webviewId === null)
        return;
      const rect = this.getBoundingClientRect();
      const newRect = {
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height
      };
      if (newRect.width === 0 && newRect.height === 0) {
        return;
      }
      if (!force && newRect.x === this.lastRect.x && newRect.y === this.lastRect.y && newRect.width === this.lastRect.width && newRect.height === this.lastRect.height) {
        return;
      }
      this.lastRect = newRect;
      const masks = [];
      this.maskSelectors.forEach((selector) => {
        try {
          document.querySelectorAll(selector).forEach((el) => {
            const mr = el.getBoundingClientRect();
            masks.push({
              x: mr.x - rect.x,
              y: mr.y - rect.y,
              width: mr.width,
              height: mr.height
            });
          });
        } catch (_e) {}
      });
      send("webviewTagResize", {
        id: this.webviewId,
        frame: newRect,
        masks: JSON.stringify(masks)
      });
    }
    loadURL(url) {
      if (this.webviewId === null)
        return;
      this.setAttribute("src", url);
      send("webviewTagUpdateSrc", { id: this.webviewId, url });
    }
    loadHTML(html) {
      if (this.webviewId === null)
        return;
      send("webviewTagUpdateHtml", { id: this.webviewId, html });
    }
    reload() {
      if (this.webviewId !== null)
        send("webviewTagReload", { id: this.webviewId });
    }
    goBack() {
      if (this.webviewId !== null)
        send("webviewTagGoBack", { id: this.webviewId });
    }
    goForward() {
      if (this.webviewId !== null)
        send("webviewTagGoForward", { id: this.webviewId });
    }
    async canGoBack() {
      if (this.webviewId === null)
        return false;
      return await request("webviewTagCanGoBack", {
        id: this.webviewId
      });
    }
    async canGoForward() {
      if (this.webviewId === null)
        return false;
      return await request("webviewTagCanGoForward", {
        id: this.webviewId
      });
    }
    toggleTransparent(value) {
      if (this.webviewId === null)
        return;
      this.transparent = value !== undefined ? value : !this.transparent;
      this.style.opacity = this.transparent ? "0" : "";
      send("webviewTagSetTransparent", {
        id: this.webviewId,
        transparent: this.transparent
      });
    }
    togglePassthrough(value) {
      if (this.webviewId === null)
        return;
      this.passthroughEnabled = value !== undefined ? value : !this.passthroughEnabled;
      this.style.pointerEvents = this.passthroughEnabled ? "none" : "";
      send("webviewTagSetPassthrough", {
        id: this.webviewId,
        enablePassthrough: this.passthroughEnabled
      });
    }
    toggleHidden(value) {
      if (this.webviewId === null)
        return;
      this.hidden = value !== undefined ? value : !this.hidden;
      send("webviewTagSetHidden", { id: this.webviewId, hidden: this.hidden });
    }
    addMaskSelector(selector) {
      this.maskSelectors.add(selector);
      this.syncDimensions(true);
    }
    removeMaskSelector(selector) {
      this.maskSelectors.delete(selector);
      this.syncDimensions(true);
    }
    setNavigationRules(rules) {
      if (this.webviewId !== null) {
        send("webviewTagSetNavigationRules", { id: this.webviewId, rules });
      }
    }
    findInPage(searchText, options) {
      if (this.webviewId === null)
        return;
      const forward = options?.forward !== false;
      const matchCase = options?.matchCase || false;
      send("webviewTagFindInPage", {
        id: this.webviewId,
        searchText,
        forward,
        matchCase
      });
    }
    stopFindInPage() {
      if (this.webviewId !== null)
        send("webviewTagStopFind", { id: this.webviewId });
    }
    openDevTools() {
      if (this.webviewId !== null)
        send("webviewTagOpenDevTools", { id: this.webviewId });
    }
    closeDevTools() {
      if (this.webviewId !== null)
        send("webviewTagCloseDevTools", { id: this.webviewId });
    }
    toggleDevTools() {
      if (this.webviewId !== null)
        send("webviewTagToggleDevTools", { id: this.webviewId });
    }
    on(event, listener) {
      if (!this._eventListeners[event])
        this._eventListeners[event] = [];
      this._eventListeners[event].push(listener);
    }
    off(event, listener) {
      if (!this._eventListeners[event])
        return;
      const idx = this._eventListeners[event].indexOf(listener);
      if (idx !== -1)
        this._eventListeners[event].splice(idx, 1);
    }
    emit(event, detail) {
      const listeners = this._eventListeners[event];
      if (listeners) {
        const customEvent = new CustomEvent(event, { detail });
        listeners.forEach((fn) => fn(customEvent));
      }
    }
    get src() {
      return this.getAttribute("src");
    }
    set src(value) {
      if (value) {
        this.setAttribute("src", value);
        if (this.webviewId !== null)
          this.loadURL(value);
      } else {
        this.removeAttribute("src");
      }
    }
    get html() {
      return this.getAttribute("html");
    }
    set html(value) {
      if (value) {
        this.setAttribute("html", value);
        if (this.webviewId !== null)
          this.loadHTML(value);
      } else {
        this.removeAttribute("html");
      }
    }
    get preload() {
      return this.getAttribute("preload");
    }
    set preload(value) {
      if (value)
        this.setAttribute("preload", value);
      else
        this.removeAttribute("preload");
    }
    get renderer() {
      return this.getAttribute("renderer") || "native";
    }
    set renderer(value) {
      this.setAttribute("renderer", value);
    }
    get sandbox() {
      return this.sandboxed;
    }
  }
  function initWebviewTag() {
    if (!customElements.get("electrobun-webview")) {
      customElements.define("electrobun-webview", ElectrobunWebviewTag);
    }
    const injectStyles = () => {
      const style = document.createElement("style");
      style.textContent = \`
electrobun-webview {
	display: block;
	width: 800px;
	height: 300px;
	background: #fff;
	background-repeat: no-repeat !important;
	overflow: hidden;
}
\`;
      if (document.head?.firstChild) {
        document.head.insertBefore(style, document.head.firstChild);
      } else if (document.head) {
        document.head.appendChild(style);
      }
    };
    if (document.head) {
      injectStyles();
    } else {
      document.addEventListener("DOMContentLoaded", injectStyles);
    }
  }

  // src/bun/preload/events.ts
  function emitWebviewEvent(eventName, detail) {
    setTimeout(() => {
      const bridge = window.__electrobunEventBridge || window.__electrobunInternalBridge;
      bridge?.postMessage(JSON.stringify({
        id: "webviewEvent",
        type: "message",
        payload: {
          id: window.__electrobunWebviewId,
          eventName,
          detail
        }
      }));
    });
  }
  function initLifecycleEvents() {
    window.addEventListener("load", () => {
      if (window === window.top) {
        emitWebviewEvent("dom-ready", document.location.href);
      }
    });
    window.addEventListener("popstate", () => {
      emitWebviewEvent("did-navigate-in-page", window.location.href);
    });
    window.addEventListener("hashchange", () => {
      emitWebviewEvent("did-navigate-in-page", window.location.href);
    });
  }
  var cmdKeyHeld = false;
  var cmdKeyTimestamp = 0;
  var CMD_KEY_THRESHOLD_MS = 500;
  function isCmdHeld() {
    if (cmdKeyHeld)
      return true;
    return Date.now() - cmdKeyTimestamp < CMD_KEY_THRESHOLD_MS && cmdKeyTimestamp > 0;
  }
  function initCmdClickHandling() {
    window.addEventListener("keydown", (event) => {
      if (event.key === "Meta" || event.metaKey) {
        cmdKeyHeld = true;
        cmdKeyTimestamp = Date.now();
      }
    }, true);
    window.addEventListener("keyup", (event) => {
      if (event.key === "Meta") {
        cmdKeyHeld = false;
        cmdKeyTimestamp = Date.now();
      }
    }, true);
    window.addEventListener("blur", () => {
      cmdKeyHeld = false;
    });
    window.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey) {
        const anchor = event.target?.closest?.("a");
        if (anchor && anchor.href) {
          event.preventDefault();
          event.stopPropagation();
          event.stopImmediatePropagation();
          emitWebviewEvent("new-window-open", JSON.stringify({
            url: anchor.href,
            isCmdClick: true,
            isSPANavigation: false
          }));
        }
      }
    }, true);
  }
  function initSPANavigationInterception() {
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    history.pushState = function(state, title, url) {
      if (isCmdHeld() && url) {
        const resolvedUrl = new URL(String(url), window.location.href).href;
        emitWebviewEvent("new-window-open", JSON.stringify({
          url: resolvedUrl,
          isCmdClick: true,
          isSPANavigation: true
        }));
        return;
      }
      return originalPushState.apply(this, [state, title, url]);
    };
    history.replaceState = function(state, title, url) {
      if (isCmdHeld() && url) {
        const resolvedUrl = new URL(String(url), window.location.href).href;
        emitWebviewEvent("new-window-open", JSON.stringify({
          url: resolvedUrl,
          isCmdClick: true,
          isSPANavigation: true
        }));
        return;
      }
      return originalReplaceState.apply(this, [state, title, url]);
    };
  }
  function initOverscrollPrevention() {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.type = "text/css";
      style.appendChild(document.createTextNode("html, body { overscroll-behavior: none; }"));
      document.head.appendChild(style);
    });
  }

  // src/bun/preload/index.ts
  initEncryption().catch((err) => console.error("Failed to initialize encryption:", err));
  var internalMessageHandler = (msg) => {
    handleResponse(msg);
  };
  if (!window.__electrobun) {
    window.__electrobun = {
      receiveInternalMessageFromBun: internalMessageHandler,
      receiveMessageFromBun: (msg) => {
        console.log("receiveMessageFromBun (no handler):", msg);
      }
    };
  } else {
    window.__electrobun.receiveInternalMessageFromBun = internalMessageHandler;
    window.__electrobun.receiveMessageFromBun = (msg) => {
      console.log("receiveMessageFromBun (no handler):", msg);
    };
  }
  window.__electrobunSendToHost = (message) => {
    emitWebviewEvent("host-message", JSON.stringify(message));
  };
  initLifecycleEvents();
  initCmdClickHandling();
  initSPANavigationInterception();
  initOverscrollPrevention();
  initDragRegions();
  initWebviewTag();
})();
`, preloadScriptSandboxed = `(() => {
  // src/bun/preload/events.ts
  function emitWebviewEvent(eventName, detail) {
    setTimeout(() => {
      const bridge = window.__electrobunEventBridge || window.__electrobunInternalBridge;
      bridge?.postMessage(JSON.stringify({
        id: "webviewEvent",
        type: "message",
        payload: {
          id: window.__electrobunWebviewId,
          eventName,
          detail
        }
      }));
    });
  }
  function initLifecycleEvents() {
    window.addEventListener("load", () => {
      if (window === window.top) {
        emitWebviewEvent("dom-ready", document.location.href);
      }
    });
    window.addEventListener("popstate", () => {
      emitWebviewEvent("did-navigate-in-page", window.location.href);
    });
    window.addEventListener("hashchange", () => {
      emitWebviewEvent("did-navigate-in-page", window.location.href);
    });
  }
  var cmdKeyHeld = false;
  var cmdKeyTimestamp = 0;
  var CMD_KEY_THRESHOLD_MS = 500;
  function isCmdHeld() {
    if (cmdKeyHeld)
      return true;
    return Date.now() - cmdKeyTimestamp < CMD_KEY_THRESHOLD_MS && cmdKeyTimestamp > 0;
  }
  function initCmdClickHandling() {
    window.addEventListener("keydown", (event) => {
      if (event.key === "Meta" || event.metaKey) {
        cmdKeyHeld = true;
        cmdKeyTimestamp = Date.now();
      }
    }, true);
    window.addEventListener("keyup", (event) => {
      if (event.key === "Meta") {
        cmdKeyHeld = false;
        cmdKeyTimestamp = Date.now();
      }
    }, true);
    window.addEventListener("blur", () => {
      cmdKeyHeld = false;
    });
    window.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey) {
        const anchor = event.target?.closest?.("a");
        if (anchor && anchor.href) {
          event.preventDefault();
          event.stopPropagation();
          event.stopImmediatePropagation();
          emitWebviewEvent("new-window-open", JSON.stringify({
            url: anchor.href,
            isCmdClick: true,
            isSPANavigation: false
          }));
        }
      }
    }, true);
  }
  function initSPANavigationInterception() {
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    history.pushState = function(state, title, url) {
      if (isCmdHeld() && url) {
        const resolvedUrl = new URL(String(url), window.location.href).href;
        emitWebviewEvent("new-window-open", JSON.stringify({
          url: resolvedUrl,
          isCmdClick: true,
          isSPANavigation: true
        }));
        return;
      }
      return originalPushState.apply(this, [state, title, url]);
    };
    history.replaceState = function(state, title, url) {
      if (isCmdHeld() && url) {
        const resolvedUrl = new URL(String(url), window.location.href).href;
        emitWebviewEvent("new-window-open", JSON.stringify({
          url: resolvedUrl,
          isCmdClick: true,
          isSPANavigation: true
        }));
        return;
      }
      return originalReplaceState.apply(this, [state, title, url]);
    };
  }
  function initOverscrollPrevention() {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.type = "text/css";
      style.appendChild(document.createTextNode("html, body { overscroll-behavior: none; }"));
      document.head.appendChild(style);
    });
  }

  // src/bun/preload/index-sandboxed.ts
  initLifecycleEvents();
  initCmdClickHandling();
  initSPANavigationInterception();
  initOverscrollPrevention();
})();
`;

// node_modules/electrobun/dist/api/bun/proc/native.ts
import { join as join4 } from "path";
import {
  dlopen,
  suffix,
  JSCallback,
  CString,
  ptr,
  FFIType,
  toArrayBuffer
} from "bun:ffi";
function storeMenuData(data) {
  const id = `menuData_${++menuDataCounter}`;
  menuDataRegistry.set(id, data);
  return id;
}
function getMenuData(id) {
  return menuDataRegistry.get(id);
}
function clearMenuData(id) {
  menuDataRegistry.delete(id);
}
function serializeMenuAction(action, data) {
  const dataId = storeMenuData(data);
  return `${ELECTROBUN_DELIMITER}${dataId}|${action}`;
}
function deserializeMenuAction(encodedAction) {
  let actualAction = encodedAction;
  let data = undefined;
  if (encodedAction.startsWith(ELECTROBUN_DELIMITER)) {
    const parts = encodedAction.split("|");
    if (parts.length >= 4) {
      const dataId = parts[2];
      actualAction = parts.slice(3).join("|");
      data = getMenuData(dataId);
      clearMenuData(dataId);
    }
  }
  return { action: actualAction, data };
}
function toCString(jsString, addNullTerminator = true) {
  let appendWith = "";
  if (addNullTerminator && !jsString.endsWith("\x00")) {
    appendWith = "\x00";
  }
  const buff = Buffer.from(jsString + appendWith, "utf8");
  return ptr(buff);
}
var menuDataRegistry, menuDataCounter = 0, ELECTROBUN_DELIMITER = "|EB|", native, ffi, windowCloseCallback, windowMoveCallback, windowResizeCallback, windowFocusCallback, getMimeType, getHTMLForWebviewSync, urlOpenCallback, quitRequestedCallback, globalShortcutHandlers, globalShortcutCallback, sessionCache, webviewDecideNavigation, webviewEventHandler = (id, eventName, detail) => {
  const webview = BrowserView.getById(id);
  if (!webview) {
    console.error("[webviewEventHandler] No webview found for id:", id);
    return;
  }
  if (webview.hostWebviewId) {
    const hostWebview = BrowserView.getById(webview.hostWebviewId);
    if (!hostWebview) {
      console.error("[webviewEventHandler] No webview found for id:", id);
      return;
    }
    let js;
    if (eventName === "new-window-open" || eventName === "host-message") {
      js = `document.querySelector('#electrobun-webview-${id}').emit(${JSON.stringify(eventName)}, ${detail});`;
    } else {
      js = `document.querySelector('#electrobun-webview-${id}').emit(${JSON.stringify(eventName)}, ${JSON.stringify(detail)});`;
    }
    native.symbols.evaluateJavaScriptWithNoCompletion(hostWebview.ptr, toCString(js));
  }
  const eventMap = {
    "will-navigate": "willNavigate",
    "did-navigate": "didNavigate",
    "did-navigate-in-page": "didNavigateInPage",
    "did-commit-navigation": "didCommitNavigation",
    "dom-ready": "domReady",
    "new-window-open": "newWindowOpen",
    "host-message": "hostMessage",
    "download-started": "downloadStarted",
    "download-progress": "downloadProgress",
    "download-completed": "downloadCompleted",
    "download-failed": "downloadFailed",
    "load-started": "loadStarted",
    "load-committed": "loadCommitted",
    "load-finished": "loadFinished"
  };
  const mappedName = eventMap[eventName];
  const handler = mappedName ? eventEmitter_default.events.webview[mappedName] : undefined;
  if (!handler) {
    return { success: false };
  }
  let parsedDetail = detail;
  if (eventName === "new-window-open" || eventName === "host-message" || eventName === "download-started" || eventName === "download-progress" || eventName === "download-completed" || eventName === "download-failed") {
    try {
      parsedDetail = JSON.parse(detail);
    } catch (e) {
      console.error("[webviewEventHandler] Failed to parse JSON:", e);
      parsedDetail = detail;
    }
  }
  const event = handler({
    detail: parsedDetail
  });
  eventEmitter_default.emitEvent(event);
  eventEmitter_default.emitEvent(event, id);
}, webviewEventJSCallback, bunBridgePostmessageHandler, eventBridgeHandler, internalBridgeHandler, trayItemHandler, applicationMenuHandler, contextMenuHandler, internalRpcHandlers;
var init_native = __esm(async () => {
  init_eventEmitter();
  await __promiseAll([
    init_BrowserView(),
    init_Tray(),
    init_BrowserWindow()
  ]);
  menuDataRegistry = new Map;
  native = (() => {
    try {
      const nativeWrapperPath = join4(process.cwd(), `libNativeWrapper.${suffix}`);
      return dlopen(nativeWrapperPath, {
        createWindowWithFrameAndStyleFromWorker: {
          args: [
            FFIType.u32,
            FFIType.f64,
            FFIType.f64,
            FFIType.f64,
            FFIType.f64,
            FFIType.u32,
            FFIType.cstring,
            FFIType.bool,
            FFIType.function,
            FFIType.function,
            FFIType.function,
            FFIType.function
          ],
          returns: FFIType.ptr
        },
        setWindowTitle: {
          args: [
            FFIType.ptr,
            FFIType.cstring
          ],
          returns: FFIType.void
        },
        showWindow: {
          args: [
            FFIType.ptr
          ],
          returns: FFIType.void
        },
        closeWindow: {
          args: [
            FFIType.ptr
          ],
          returns: FFIType.void
        },
        minimizeWindow: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        restoreWindow: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        isWindowMinimized: {
          args: [FFIType.ptr],
          returns: FFIType.bool
        },
        maximizeWindow: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        unmaximizeWindow: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        isWindowMaximized: {
          args: [FFIType.ptr],
          returns: FFIType.bool
        },
        setWindowFullScreen: {
          args: [FFIType.ptr, FFIType.bool],
          returns: FFIType.void
        },
        isWindowFullScreen: {
          args: [FFIType.ptr],
          returns: FFIType.bool
        },
        setWindowAlwaysOnTop: {
          args: [FFIType.ptr, FFIType.bool],
          returns: FFIType.void
        },
        isWindowAlwaysOnTop: {
          args: [FFIType.ptr],
          returns: FFIType.bool
        },
        setWindowPosition: {
          args: [FFIType.ptr, FFIType.f64, FFIType.f64],
          returns: FFIType.void
        },
        setWindowSize: {
          args: [FFIType.ptr, FFIType.f64, FFIType.f64],
          returns: FFIType.void
        },
        setWindowFrame: {
          args: [FFIType.ptr, FFIType.f64, FFIType.f64, FFIType.f64, FFIType.f64],
          returns: FFIType.void
        },
        getWindowFrame: {
          args: [FFIType.ptr, FFIType.ptr, FFIType.ptr, FFIType.ptr, FFIType.ptr],
          returns: FFIType.void
        },
        initWebview: {
          args: [
            FFIType.u32,
            FFIType.ptr,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.f64,
            FFIType.f64,
            FFIType.f64,
            FFIType.f64,
            FFIType.bool,
            FFIType.cstring,
            FFIType.function,
            FFIType.function,
            FFIType.function,
            FFIType.function,
            FFIType.function,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.bool,
            FFIType.bool
          ],
          returns: FFIType.ptr
        },
        setNextWebviewFlags: {
          args: [
            FFIType.bool,
            FFIType.bool
          ],
          returns: FFIType.void
        },
        webviewCanGoBack: {
          args: [FFIType.ptr],
          returns: FFIType.bool
        },
        webviewCanGoForward: {
          args: [FFIType.ptr],
          returns: FFIType.bool
        },
        resizeWebview: {
          args: [
            FFIType.ptr,
            FFIType.f64,
            FFIType.f64,
            FFIType.f64,
            FFIType.f64,
            FFIType.cstring
          ],
          returns: FFIType.void
        },
        loadURLInWebView: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        loadHTMLInWebView: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        updatePreloadScriptToWebView: {
          args: [
            FFIType.ptr,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.bool
          ],
          returns: FFIType.void
        },
        webviewGoBack: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        webviewGoForward: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        webviewReload: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        webviewRemove: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        setWebviewHTMLContent: {
          args: [FFIType.u32, FFIType.cstring],
          returns: FFIType.void
        },
        startWindowMove: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        stopWindowMove: {
          args: [],
          returns: FFIType.void
        },
        webviewSetTransparent: {
          args: [FFIType.ptr, FFIType.bool],
          returns: FFIType.void
        },
        webviewSetPassthrough: {
          args: [FFIType.ptr, FFIType.bool],
          returns: FFIType.void
        },
        webviewSetHidden: {
          args: [FFIType.ptr, FFIType.bool],
          returns: FFIType.void
        },
        setWebviewNavigationRules: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        webviewFindInPage: {
          args: [FFIType.ptr, FFIType.cstring, FFIType.bool, FFIType.bool],
          returns: FFIType.void
        },
        webviewStopFind: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        evaluateJavaScriptWithNoCompletion: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        webviewOpenDevTools: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        webviewCloseDevTools: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        webviewToggleDevTools: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        createTray: {
          args: [
            FFIType.u32,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.bool,
            FFIType.u32,
            FFIType.u32,
            FFIType.function
          ],
          returns: FFIType.ptr
        },
        setTrayTitle: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        setTrayImage: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        setTrayMenu: {
          args: [FFIType.ptr, FFIType.cstring],
          returns: FFIType.void
        },
        removeTray: {
          args: [FFIType.ptr],
          returns: FFIType.void
        },
        setApplicationMenu: {
          args: [FFIType.cstring, FFIType.function],
          returns: FFIType.void
        },
        showContextMenu: {
          args: [FFIType.cstring, FFIType.function],
          returns: FFIType.void
        },
        moveToTrash: {
          args: [FFIType.cstring],
          returns: FFIType.bool
        },
        showItemInFolder: {
          args: [FFIType.cstring],
          returns: FFIType.void
        },
        openExternal: {
          args: [FFIType.cstring],
          returns: FFIType.bool
        },
        openPath: {
          args: [FFIType.cstring],
          returns: FFIType.bool
        },
        showNotification: {
          args: [
            FFIType.cstring,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.bool
          ],
          returns: FFIType.void
        },
        setGlobalShortcutCallback: {
          args: [FFIType.function],
          returns: FFIType.void
        },
        registerGlobalShortcut: {
          args: [FFIType.cstring],
          returns: FFIType.bool
        },
        unregisterGlobalShortcut: {
          args: [FFIType.cstring],
          returns: FFIType.bool
        },
        unregisterAllGlobalShortcuts: {
          args: [],
          returns: FFIType.void
        },
        isGlobalShortcutRegistered: {
          args: [FFIType.cstring],
          returns: FFIType.bool
        },
        getAllDisplays: {
          args: [],
          returns: FFIType.cstring
        },
        getPrimaryDisplay: {
          args: [],
          returns: FFIType.cstring
        },
        getCursorScreenPoint: {
          args: [],
          returns: FFIType.cstring
        },
        openFileDialog: {
          args: [
            FFIType.cstring,
            FFIType.cstring,
            FFIType.int,
            FFIType.int,
            FFIType.int
          ],
          returns: FFIType.cstring
        },
        showMessageBox: {
          args: [
            FFIType.cstring,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.cstring,
            FFIType.int,
            FFIType.int
          ],
          returns: FFIType.int
        },
        clipboardReadText: {
          args: [],
          returns: FFIType.cstring
        },
        clipboardWriteText: {
          args: [FFIType.cstring],
          returns: FFIType.void
        },
        clipboardReadImage: {
          args: [FFIType.ptr],
          returns: FFIType.ptr
        },
        clipboardWriteImage: {
          args: [FFIType.ptr, FFIType.u64],
          returns: FFIType.void
        },
        clipboardClear: {
          args: [],
          returns: FFIType.void
        },
        clipboardAvailableFormats: {
          args: [],
          returns: FFIType.cstring
        },
        sessionGetCookies: {
          args: [FFIType.cstring, FFIType.cstring],
          returns: FFIType.cstring
        },
        sessionSetCookie: {
          args: [FFIType.cstring, FFIType.cstring],
          returns: FFIType.bool
        },
        sessionRemoveCookie: {
          args: [FFIType.cstring, FFIType.cstring, FFIType.cstring],
          returns: FFIType.bool
        },
        sessionClearCookies: {
          args: [FFIType.cstring],
          returns: FFIType.void
        },
        sessionClearStorageData: {
          args: [FFIType.cstring, FFIType.cstring],
          returns: FFIType.void
        },
        setURLOpenHandler: {
          args: [FFIType.function],
          returns: FFIType.void
        },
        getWindowStyle: {
          args: [
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool,
            FFIType.bool
          ],
          returns: FFIType.u32
        },
        setJSUtils: {
          args: [
            FFIType.function,
            FFIType.function
          ],
          returns: FFIType.void
        },
        setWindowIcon: {
          args: [
            FFIType.ptr,
            FFIType.cstring
          ],
          returns: FFIType.void
        },
        killApp: {
          args: [],
          returns: FFIType.void
        },
        stopEventLoop: {
          args: [],
          returns: FFIType.void
        },
        waitForShutdownComplete: {
          args: [FFIType.i32],
          returns: FFIType.void
        },
        forceExit: {
          args: [FFIType.i32],
          returns: FFIType.void
        },
        setQuitRequestedHandler: {
          args: [FFIType.function],
          returns: FFIType.void
        },
        testFFI2: {
          args: [FFIType.function],
          returns: FFIType.void
        }
      });
    } catch (err) {
      console.log("FATAL Error opening native FFI:", err.message);
      console.log("This may be due to:");
      console.log("  - Missing libNativeWrapper.dll/so/dylib");
      console.log("  - Architecture mismatch (ARM64 vs x64)");
      console.log("  - Missing WebView2 or CEF dependencies");
      if (suffix === "so") {
        console.log("  - Missing system libraries (try: ldd ./libNativeWrapper.so)");
      }
      console.log("Check that the build process completed successfully for your architecture.");
      process.exit();
    }
  })();
  ffi = {
    request: {
      createWindow: (params) => {
        const {
          id,
          url: _url,
          title,
          frame: { x, y, width, height },
          styleMask: {
            Borderless,
            Titled,
            Closable,
            Miniaturizable,
            Resizable,
            UnifiedTitleAndToolbar,
            FullScreen,
            FullSizeContentView,
            UtilityWindow,
            DocModalWindow,
            NonactivatingPanel,
            HUDWindow
          },
          titleBarStyle,
          transparent
        } = params;
        const styleMask = native.symbols.getWindowStyle(Borderless, Titled, Closable, Miniaturizable, Resizable, UnifiedTitleAndToolbar, FullScreen, FullSizeContentView, UtilityWindow, DocModalWindow, NonactivatingPanel, HUDWindow);
        const windowPtr = native.symbols.createWindowWithFrameAndStyleFromWorker(id, x, y, width, height, styleMask, toCString(titleBarStyle), transparent, windowCloseCallback, windowMoveCallback, windowResizeCallback, windowFocusCallback);
        if (!windowPtr) {
          throw "Failed to create window";
        }
        native.symbols.setWindowTitle(windowPtr, toCString(title));
        native.symbols.showWindow(windowPtr);
        return windowPtr;
      },
      setTitle: (params) => {
        const { winId, title } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't add webview to window. window no longer exists`;
        }
        native.symbols.setWindowTitle(windowPtr, toCString(title));
      },
      closeWindow: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't close window. Window no longer exists`;
        }
        native.symbols.closeWindow(windowPtr);
      },
      focusWindow: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't focus window. Window no longer exists`;
        }
        native.symbols.showWindow(windowPtr);
      },
      minimizeWindow: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't minimize window. Window no longer exists`;
        }
        native.symbols.minimizeWindow(windowPtr);
      },
      restoreWindow: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't restore window. Window no longer exists`;
        }
        native.symbols.restoreWindow(windowPtr);
      },
      isWindowMinimized: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          return false;
        }
        return native.symbols.isWindowMinimized(windowPtr);
      },
      maximizeWindow: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't maximize window. Window no longer exists`;
        }
        native.symbols.maximizeWindow(windowPtr);
      },
      unmaximizeWindow: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't unmaximize window. Window no longer exists`;
        }
        native.symbols.unmaximizeWindow(windowPtr);
      },
      isWindowMaximized: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          return false;
        }
        return native.symbols.isWindowMaximized(windowPtr);
      },
      setWindowFullScreen: (params) => {
        const { winId, fullScreen } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't set fullscreen. Window no longer exists`;
        }
        native.symbols.setWindowFullScreen(windowPtr, fullScreen);
      },
      isWindowFullScreen: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          return false;
        }
        return native.symbols.isWindowFullScreen(windowPtr);
      },
      setWindowAlwaysOnTop: (params) => {
        const { winId, alwaysOnTop } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't set always on top. Window no longer exists`;
        }
        native.symbols.setWindowAlwaysOnTop(windowPtr, alwaysOnTop);
      },
      isWindowAlwaysOnTop: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          return false;
        }
        return native.symbols.isWindowAlwaysOnTop(windowPtr);
      },
      setWindowPosition: (params) => {
        const { winId, x, y } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't set window position. Window no longer exists`;
        }
        native.symbols.setWindowPosition(windowPtr, x, y);
      },
      setWindowSize: (params) => {
        const { winId, width, height } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't set window size. Window no longer exists`;
        }
        native.symbols.setWindowSize(windowPtr, width, height);
      },
      setWindowFrame: (params) => {
        const { winId, x, y, width, height } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          throw `Can't set window frame. Window no longer exists`;
        }
        native.symbols.setWindowFrame(windowPtr, x, y, width, height);
      },
      getWindowFrame: (params) => {
        const { winId } = params;
        const windowPtr = BrowserWindow.getById(winId)?.ptr;
        if (!windowPtr) {
          return { x: 0, y: 0, width: 0, height: 0 };
        }
        const xBuf = new Float64Array(1);
        const yBuf = new Float64Array(1);
        const widthBuf = new Float64Array(1);
        const heightBuf = new Float64Array(1);
        native.symbols.getWindowFrame(windowPtr, ptr(xBuf), ptr(yBuf), ptr(widthBuf), ptr(heightBuf));
        return {
          x: xBuf[0],
          y: yBuf[0],
          width: widthBuf[0],
          height: heightBuf[0]
        };
      },
      createWebview: (params) => {
        const {
          id,
          windowId,
          renderer,
          rpcPort: rpcPort2,
          secretKey,
          url,
          partition,
          preload,
          frame: { x, y, width, height },
          autoResize,
          sandbox,
          startTransparent,
          startPassthrough
        } = params;
        const parentWindow = BrowserWindow.getById(windowId);
        const windowPtr = parentWindow?.ptr;
        const transparent = parentWindow?.transparent ?? false;
        if (!windowPtr) {
          throw `Can't add webview to window. window no longer exists`;
        }
        let dynamicPreload;
        let selectedPreloadScript;
        if (sandbox) {
          dynamicPreload = `
window.__electrobunWebviewId = ${id};
window.__electrobunWindowId = ${windowId};
window.__electrobunEventBridge = window.__electrobunEventBridge || window.webkit?.messageHandlers?.eventBridge || window.eventBridge || window.chrome?.webview?.hostObjects?.eventBridge;
window.__electrobunInternalBridge = window.__electrobunInternalBridge || window.webkit?.messageHandlers?.internalBridge || window.internalBridge || window.chrome?.webview?.hostObjects?.internalBridge;
`;
          selectedPreloadScript = preloadScriptSandboxed;
        } else {
          dynamicPreload = `
window.__electrobunWebviewId = ${id};
window.__electrobunWindowId = ${windowId};
window.__electrobunRpcSocketPort = ${rpcPort2};
window.__electrobunSecretKeyBytes = [${secretKey}];
window.__electrobunEventBridge = window.__electrobunEventBridge || window.webkit?.messageHandlers?.eventBridge || window.eventBridge || window.chrome?.webview?.hostObjects?.eventBridge;
window.__electrobunInternalBridge = window.__electrobunInternalBridge || window.webkit?.messageHandlers?.internalBridge || window.internalBridge || window.chrome?.webview?.hostObjects?.internalBridge;
window.__electrobunBunBridge = window.__electrobunBunBridge || window.webkit?.messageHandlers?.bunBridge || window.bunBridge || window.chrome?.webview?.hostObjects?.bunBridge;
`;
          selectedPreloadScript = preloadScript;
        }
        const electrobunPreload = dynamicPreload + selectedPreloadScript;
        const customPreload = preload;
        native.symbols.setNextWebviewFlags(startTransparent, startPassthrough);
        const webviewPtr = native.symbols.initWebview(id, windowPtr, toCString(renderer), toCString(url || ""), x, y, width, height, autoResize, toCString(partition || "persist:default"), webviewDecideNavigation, webviewEventJSCallback, eventBridgeHandler, bunBridgePostmessageHandler, internalBridgeHandler, toCString(electrobunPreload), toCString(customPreload || ""), transparent, sandbox);
        if (!webviewPtr) {
          throw "Failed to create webview";
        }
        return webviewPtr;
      },
      evaluateJavascriptWithNoCompletion: (params) => {
        const { id, js } = params;
        const webview = BrowserView.getById(id);
        if (!webview?.ptr) {
          return;
        }
        native.symbols.evaluateJavaScriptWithNoCompletion(webview.ptr, toCString(js));
      },
      createTray: (params) => {
        const { id, title, image, template, width, height } = params;
        const trayPtr = native.symbols.createTray(id, toCString(title), toCString(image), template, width, height, trayItemHandler);
        if (!trayPtr) {
          throw "Failed to create tray";
        }
        return trayPtr;
      },
      setTrayTitle: (params) => {
        const { id, title } = params;
        const tray = Tray.getById(id);
        if (!tray)
          return;
        native.symbols.setTrayTitle(tray.ptr, toCString(title));
      },
      setTrayImage: (params) => {
        const { id, image } = params;
        const tray = Tray.getById(id);
        if (!tray)
          return;
        native.symbols.setTrayImage(tray.ptr, toCString(image));
      },
      setTrayMenu: (params) => {
        const { id, menuConfig } = params;
        const tray = Tray.getById(id);
        if (!tray)
          return;
        native.symbols.setTrayMenu(tray.ptr, toCString(menuConfig));
      },
      removeTray: (params) => {
        const { id } = params;
        const tray = Tray.getById(id);
        if (!tray) {
          throw `Can't remove tray. Tray no longer exists`;
        }
        native.symbols.removeTray(tray.ptr);
      },
      setApplicationMenu: (params) => {
        const { menuConfig } = params;
        native.symbols.setApplicationMenu(toCString(menuConfig), applicationMenuHandler);
      },
      showContextMenu: (params) => {
        const { menuConfig } = params;
        native.symbols.showContextMenu(toCString(menuConfig), contextMenuHandler);
      },
      moveToTrash: (params) => {
        const { path } = params;
        return native.symbols.moveToTrash(toCString(path));
      },
      showItemInFolder: (params) => {
        const { path } = params;
        native.symbols.showItemInFolder(toCString(path));
      },
      openExternal: (params) => {
        const { url } = params;
        return native.symbols.openExternal(toCString(url));
      },
      openPath: (params) => {
        const { path } = params;
        return native.symbols.openPath(toCString(path));
      },
      showNotification: (params) => {
        const { title, body = "", subtitle = "", silent = false } = params;
        native.symbols.showNotification(toCString(title), toCString(body), toCString(subtitle), silent);
      },
      openFileDialog: (params) => {
        const {
          startingFolder,
          allowedFileTypes,
          canChooseFiles,
          canChooseDirectory,
          allowsMultipleSelection
        } = params;
        const filePath = native.symbols.openFileDialog(toCString(startingFolder), toCString(allowedFileTypes), canChooseFiles ? 1 : 0, canChooseDirectory ? 1 : 0, allowsMultipleSelection ? 1 : 0);
        return filePath.toString();
      },
      showMessageBox: (params) => {
        const {
          type = "info",
          title = "",
          message = "",
          detail = "",
          buttons = ["OK"],
          defaultId = 0,
          cancelId = -1
        } = params;
        const buttonsStr = buttons.join(",");
        return native.symbols.showMessageBox(toCString(type), toCString(title), toCString(message), toCString(detail), toCString(buttonsStr), defaultId, cancelId);
      },
      clipboardReadText: () => {
        const result = native.symbols.clipboardReadText();
        if (!result)
          return null;
        return result.toString();
      },
      clipboardWriteText: (params) => {
        native.symbols.clipboardWriteText(toCString(params.text));
      },
      clipboardReadImage: () => {
        const sizeBuffer = new BigUint64Array(1);
        const dataPtr = native.symbols.clipboardReadImage(ptr(sizeBuffer));
        if (!dataPtr)
          return null;
        const size = Number(sizeBuffer[0]);
        if (size === 0)
          return null;
        const result = new Uint8Array(size);
        const sourceView = new Uint8Array(toArrayBuffer(dataPtr, 0, size));
        result.set(sourceView);
        return result;
      },
      clipboardWriteImage: (params) => {
        const { pngData } = params;
        native.symbols.clipboardWriteImage(ptr(pngData), BigInt(pngData.length));
      },
      clipboardClear: () => {
        native.symbols.clipboardClear();
      },
      clipboardAvailableFormats: () => {
        const result = native.symbols.clipboardAvailableFormats();
        if (!result)
          return [];
        const formatsStr = result.toString();
        if (!formatsStr)
          return [];
        return formatsStr.split(",").filter((f) => f.length > 0);
      }
    },
    internal: {
      storeMenuData,
      getMenuData,
      clearMenuData,
      serializeMenuAction,
      deserializeMenuAction
    }
  };
  process.on("uncaughtException", (err) => {
    console.error("Uncaught exception in worker:", err);
    native.symbols.stopEventLoop();
    native.symbols.waitForShutdownComplete(5000);
    native.symbols.forceExit(1);
  });
  process.on("unhandledRejection", (reason, _promise) => {
    console.error("Unhandled rejection in worker:", reason);
  });
  process.on("SIGINT", () => {
    console.log("[electrobun] Received SIGINT, running quit sequence...");
    const { quit: quit2 } = (init_Utils(), __toCommonJS(exports_Utils));
    quit2();
  });
  process.on("SIGTERM", () => {
    console.log("[electrobun] Received SIGTERM, running quit sequence...");
    const { quit: quit2 } = (init_Utils(), __toCommonJS(exports_Utils));
    quit2();
  });
  windowCloseCallback = new JSCallback((id) => {
    const handler = eventEmitter_default.events.window.close;
    const event = handler({
      id
    });
    eventEmitter_default.emitEvent(event, id);
    eventEmitter_default.emitEvent(event);
  }, {
    args: ["u32"],
    returns: "void",
    threadsafe: true
  });
  windowMoveCallback = new JSCallback((id, x, y) => {
    const handler = eventEmitter_default.events.window.move;
    const event = handler({
      id,
      x,
      y
    });
    eventEmitter_default.emitEvent(event);
    eventEmitter_default.emitEvent(event, id);
  }, {
    args: ["u32", "f64", "f64"],
    returns: "void",
    threadsafe: true
  });
  windowResizeCallback = new JSCallback((id, x, y, width, height) => {
    const handler = eventEmitter_default.events.window.resize;
    const event = handler({
      id,
      x,
      y,
      width,
      height
    });
    eventEmitter_default.emitEvent(event);
    eventEmitter_default.emitEvent(event, id);
  }, {
    args: ["u32", "f64", "f64", "f64", "f64"],
    returns: "void",
    threadsafe: true
  });
  windowFocusCallback = new JSCallback((id) => {
    const handler = eventEmitter_default.events.window.focus;
    const event = handler({
      id
    });
    eventEmitter_default.emitEvent(event);
    eventEmitter_default.emitEvent(event, id);
  }, {
    args: ["u32"],
    returns: "void",
    threadsafe: true
  });
  getMimeType = new JSCallback((filePath) => {
    const _filePath = new CString(filePath).toString();
    const mimeType = Bun.file(_filePath).type;
    return toCString(mimeType.split(";")[0]);
  }, {
    args: [FFIType.cstring],
    returns: FFIType.cstring
  });
  getHTMLForWebviewSync = new JSCallback((webviewId) => {
    const webview = BrowserView.getById(webviewId);
    return toCString(webview?.html || "");
  }, {
    args: [FFIType.u32],
    returns: FFIType.cstring
  });
  native.symbols.setJSUtils(getMimeType, getHTMLForWebviewSync);
  urlOpenCallback = new JSCallback((urlPtr) => {
    const url = new CString(urlPtr).toString();
    const handler = eventEmitter_default.events.app.openUrl;
    const event = handler({ url });
    eventEmitter_default.emitEvent(event);
  }, {
    args: [FFIType.cstring],
    returns: "void",
    threadsafe: true
  });
  if (process.platform === "darwin") {
    native.symbols.setURLOpenHandler(urlOpenCallback);
  }
  quitRequestedCallback = new JSCallback(() => {
    const { quit: quit2 } = (init_Utils(), __toCommonJS(exports_Utils));
    quit2();
  }, {
    args: [],
    returns: "void",
    threadsafe: true
  });
  native.symbols.setQuitRequestedHandler(quitRequestedCallback);
  globalShortcutHandlers = new Map;
  globalShortcutCallback = new JSCallback((acceleratorPtr) => {
    const accelerator = new CString(acceleratorPtr).toString();
    const handler = globalShortcutHandlers.get(accelerator);
    if (handler) {
      handler();
    }
  }, {
    args: [FFIType.cstring],
    returns: "void",
    threadsafe: true
  });
  native.symbols.setGlobalShortcutCallback(globalShortcutCallback);
  sessionCache = new Map;
  webviewDecideNavigation = new JSCallback((_webviewId, _url) => {
    return true;
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.u32,
    threadsafe: true
  });
  webviewEventJSCallback = new JSCallback((id, _eventName, _detail) => {
    let eventName = "";
    let detail = "";
    try {
      eventName = new CString(_eventName).toString();
      detail = new CString(_detail).toString();
    } catch (err) {
      console.error("[webviewEventJSCallback] Error converting strings:", err);
      console.error("[webviewEventJSCallback] Raw values:", {
        _eventName,
        _detail
      });
      return;
    }
    webviewEventHandler(id, eventName, detail);
  }, {
    args: [FFIType.u32, FFIType.cstring, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  bunBridgePostmessageHandler = new JSCallback((id, msg2) => {
    try {
      const msgStr = new CString(msg2);
      if (!msgStr.length) {
        return;
      }
      const msgJson = JSON.parse(msgStr.toString());
      const webview = BrowserView.getById(id);
      if (!webview)
        return;
      webview.rpcHandler?.(msgJson);
    } catch (err) {
      console.error("error sending message to bun: ", err);
      console.error("msgString: ", new CString(msg2));
    }
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  eventBridgeHandler = new JSCallback((_id, msg2) => {
    try {
      const message = new CString(msg2);
      const jsonMessage = JSON.parse(message.toString());
      if (jsonMessage.id === "webviewEvent") {
        const { payload } = jsonMessage;
        webviewEventHandler(payload.id, payload.eventName, payload.detail);
      }
    } catch (err) {
      console.error("error in eventBridgeHandler: ", err);
    }
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  internalBridgeHandler = new JSCallback((_id, msg2) => {
    try {
      const batchMessage = new CString(msg2);
      const jsonBatch = JSON.parse(batchMessage.toString());
      if (jsonBatch.id === "webviewEvent") {
        const { payload } = jsonBatch;
        webviewEventHandler(payload.id, payload.eventName, payload.detail);
        return;
      }
      jsonBatch.forEach((msgStr) => {
        const msgJson = JSON.parse(msgStr);
        if (msgJson.type === "message") {
          const handler = internalRpcHandlers.message[msgJson.id];
          handler?.(msgJson.payload);
        } else if (msgJson.type === "request") {
          const hostWebview = BrowserView.getById(msgJson.hostWebviewId);
          const handler = internalRpcHandlers.request[msgJson.method];
          const payload = handler?.(msgJson.params);
          const resultObj = {
            type: "response",
            id: msgJson.id,
            success: true,
            payload
          };
          if (!hostWebview) {
            console.log("--->>> internal request in bun: NO HOST WEBVIEW FOUND");
            return;
          }
          hostWebview.sendInternalMessageViaExecute(resultObj);
        }
      });
    } catch (err) {
      console.error("error in internalBridgeHandler: ", err);
    }
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  trayItemHandler = new JSCallback((id, action) => {
    const actionString = (new CString(action).toString() || "").trim();
    const { action: actualAction, data } = deserializeMenuAction(actionString);
    const event = eventEmitter_default.events.tray.trayClicked({
      id,
      action: actualAction,
      data
    });
    eventEmitter_default.emitEvent(event);
    eventEmitter_default.emitEvent(event, id);
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  applicationMenuHandler = new JSCallback((id, action) => {
    const actionString = new CString(action).toString();
    const { action: actualAction, data } = deserializeMenuAction(actionString);
    const event = eventEmitter_default.events.app.applicationMenuClicked({
      id,
      action: actualAction,
      data
    });
    eventEmitter_default.emitEvent(event);
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  contextMenuHandler = new JSCallback((_id, action) => {
    const actionString = new CString(action).toString();
    const { action: actualAction, data } = deserializeMenuAction(actionString);
    const event = eventEmitter_default.events.app.contextMenuClicked({
      action: actualAction,
      data
    });
    eventEmitter_default.emitEvent(event);
  }, {
    args: [FFIType.u32, FFIType.cstring],
    returns: FFIType.void,
    threadsafe: true
  });
  internalRpcHandlers = {
    request: {
      webviewTagInit: (params) => {
        const {
          hostWebviewId,
          windowId,
          renderer,
          html,
          preload,
          partition,
          frame,
          navigationRules,
          sandbox,
          transparent,
          passthrough
        } = params;
        const url = !params.url && !html ? "https://electrobun.dev" : params.url;
        const webviewForTag = new BrowserView({
          url,
          html,
          preload,
          partition,
          frame,
          hostWebviewId,
          autoResize: false,
          windowId,
          renderer,
          navigationRules,
          sandbox,
          startTransparent: transparent,
          startPassthrough: passthrough
        });
        return webviewForTag.id;
      },
      webviewTagCanGoBack: (params) => {
        const { id } = params;
        const webviewPtr = BrowserView.getById(id)?.ptr;
        if (!webviewPtr) {
          console.error("no webview ptr");
          return false;
        }
        return native.symbols.webviewCanGoBack(webviewPtr);
      },
      webviewTagCanGoForward: (params) => {
        const { id } = params;
        const webviewPtr = BrowserView.getById(id)?.ptr;
        if (!webviewPtr) {
          console.error("no webview ptr");
          return false;
        }
        return native.symbols.webviewCanGoForward(webviewPtr);
      }
    },
    message: {
      webviewTagResize: (params) => {
        const browserView = BrowserView.getById(params.id);
        const webviewPtr = browserView?.ptr;
        if (!webviewPtr) {
          console.log("[Bun] ERROR: webviewTagResize - no webview ptr found for id:", params.id);
          return;
        }
        const { x, y, width, height } = params.frame;
        native.symbols.resizeWebview(webviewPtr, x, y, width, height, toCString(params.masks));
      },
      webviewTagUpdateSrc: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagUpdateSrc: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.loadURLInWebView(webview.ptr, toCString(params.url));
      },
      webviewTagUpdateHtml: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagUpdateHtml: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.setWebviewHTMLContent(webview.id, toCString(params.html));
        webview.loadHTML(params.html);
        webview.html = params.html;
      },
      webviewTagUpdatePreload: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagUpdatePreload: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.updatePreloadScriptToWebView(webview.ptr, toCString("electrobun_custom_preload_script"), toCString(params.preload), true);
      },
      webviewTagGoBack: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagGoBack: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewGoBack(webview.ptr);
      },
      webviewTagGoForward: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagGoForward: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewGoForward(webview.ptr);
      },
      webviewTagReload: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagReload: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewReload(webview.ptr);
      },
      webviewTagRemove: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagRemove: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewRemove(webview.ptr);
      },
      startWindowMove: (params) => {
        const window = BrowserWindow.getById(params.id);
        if (!window)
          return;
        native.symbols.startWindowMove(window.ptr);
      },
      stopWindowMove: (_params) => {
        native.symbols.stopWindowMove();
      },
      webviewTagSetTransparent: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagSetTransparent: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewSetTransparent(webview.ptr, params.transparent);
      },
      webviewTagSetPassthrough: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagSetPassthrough: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewSetPassthrough(webview.ptr, params.enablePassthrough);
      },
      webviewTagSetHidden: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagSetHidden: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewSetHidden(webview.ptr, params.hidden);
      },
      webviewTagSetNavigationRules: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagSetNavigationRules: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        const rulesJson = JSON.stringify(params.rules);
        native.symbols.setWebviewNavigationRules(webview.ptr, toCString(rulesJson));
      },
      webviewTagFindInPage: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagFindInPage: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewFindInPage(webview.ptr, toCString(params.searchText), params.forward, params.matchCase);
      },
      webviewTagStopFind: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagStopFind: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewStopFind(webview.ptr);
      },
      webviewTagOpenDevTools: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagOpenDevTools: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewOpenDevTools(webview.ptr);
      },
      webviewTagCloseDevTools: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagCloseDevTools: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewCloseDevTools(webview.ptr);
      },
      webviewTagToggleDevTools: (params) => {
        const webview = BrowserView.getById(params.id);
        if (!webview || !webview.ptr) {
          console.error(`webviewTagToggleDevTools: BrowserView not found or has no ptr for id ${params.id}`);
          return;
        }
        native.symbols.webviewToggleDevTools(webview.ptr);
      },
      webviewEvent: (params) => {
        console.log("-----------------+webviewEvent", params);
      }
    }
  };
});

// node_modules/electrobun/dist/api/bun/core/BrowserWindow.ts
class BrowserWindow {
  id = nextWindowId++;
  ptr;
  title = "Electrobun";
  state = "creating";
  url = null;
  html = null;
  preload = null;
  renderer = "native";
  transparent = false;
  navigationRules = null;
  sandbox = false;
  frame = {
    x: 0,
    y: 0,
    width: 800,
    height: 600
  };
  webviewId;
  constructor(options = defaultOptions2) {
    this.title = options.title || "New Window";
    this.frame = options.frame ? { ...defaultOptions2.frame, ...options.frame } : { ...defaultOptions2.frame };
    this.url = options.url || null;
    this.html = options.html || null;
    this.preload = options.preload || null;
    this.renderer = options.renderer || defaultOptions2.renderer;
    this.transparent = options.transparent ?? false;
    this.navigationRules = options.navigationRules || null;
    this.sandbox = options.sandbox ?? false;
    this.init(options);
  }
  init({
    rpc,
    styleMask,
    titleBarStyle,
    transparent
  }) {
    this.ptr = ffi.request.createWindow({
      id: this.id,
      title: this.title,
      url: this.url || "",
      frame: {
        width: this.frame.width,
        height: this.frame.height,
        x: this.frame.x,
        y: this.frame.y
      },
      styleMask: {
        Borderless: false,
        Titled: true,
        Closable: true,
        Miniaturizable: true,
        Resizable: true,
        UnifiedTitleAndToolbar: false,
        FullScreen: false,
        FullSizeContentView: false,
        UtilityWindow: false,
        DocModalWindow: false,
        NonactivatingPanel: false,
        HUDWindow: false,
        ...styleMask || {},
        ...titleBarStyle === "hiddenInset" ? {
          Titled: true,
          FullSizeContentView: true
        } : {},
        ...titleBarStyle === "hidden" ? {
          Titled: false,
          FullSizeContentView: true
        } : {}
      },
      titleBarStyle: titleBarStyle || "default",
      transparent: transparent ?? false
    });
    BrowserWindowMap[this.id] = this;
    const webview = new BrowserView({
      url: this.url,
      html: this.html,
      preload: this.preload,
      renderer: this.renderer,
      frame: {
        x: 0,
        y: 0,
        width: this.frame.width,
        height: this.frame.height
      },
      rpc,
      windowId: this.id,
      navigationRules: this.navigationRules,
      sandbox: this.sandbox
    });
    console.log("setting webviewId: ", webview.id);
    this.webviewId = webview.id;
  }
  get webview() {
    return BrowserView.getById(this.webviewId);
  }
  static getById(id) {
    return BrowserWindowMap[id];
  }
  setTitle(title) {
    this.title = title;
    return ffi.request.setTitle({ winId: this.id, title });
  }
  close() {
    return ffi.request.closeWindow({ winId: this.id });
  }
  focus() {
    return ffi.request.focusWindow({ winId: this.id });
  }
  show() {
    return ffi.request.focusWindow({ winId: this.id });
  }
  minimize() {
    return ffi.request.minimizeWindow({ winId: this.id });
  }
  unminimize() {
    return ffi.request.restoreWindow({ winId: this.id });
  }
  isMinimized() {
    return ffi.request.isWindowMinimized({ winId: this.id });
  }
  maximize() {
    return ffi.request.maximizeWindow({ winId: this.id });
  }
  unmaximize() {
    return ffi.request.unmaximizeWindow({ winId: this.id });
  }
  isMaximized() {
    return ffi.request.isWindowMaximized({ winId: this.id });
  }
  setFullScreen(fullScreen) {
    return ffi.request.setWindowFullScreen({ winId: this.id, fullScreen });
  }
  isFullScreen() {
    return ffi.request.isWindowFullScreen({ winId: this.id });
  }
  setAlwaysOnTop(alwaysOnTop) {
    return ffi.request.setWindowAlwaysOnTop({ winId: this.id, alwaysOnTop });
  }
  isAlwaysOnTop() {
    return ffi.request.isWindowAlwaysOnTop({ winId: this.id });
  }
  setPosition(x, y) {
    this.frame.x = x;
    this.frame.y = y;
    return ffi.request.setWindowPosition({ winId: this.id, x, y });
  }
  setSize(width, height) {
    this.frame.width = width;
    this.frame.height = height;
    return ffi.request.setWindowSize({ winId: this.id, width, height });
  }
  setFrame(x, y, width, height) {
    this.frame = { x, y, width, height };
    return ffi.request.setWindowFrame({ winId: this.id, x, y, width, height });
  }
  getFrame() {
    const frame = ffi.request.getWindowFrame({ winId: this.id });
    this.frame = frame;
    return frame;
  }
  getPosition() {
    const frame = this.getFrame();
    return { x: frame.x, y: frame.y };
  }
  getSize() {
    const frame = this.getFrame();
    return { width: frame.width, height: frame.height };
  }
  on(name, handler) {
    const specificName = `${name}-${this.id}`;
    eventEmitter_default.on(specificName, handler);
  }
}
var buildConfig3, nextWindowId = 1, defaultOptions2, BrowserWindowMap;
var init_BrowserWindow = __esm(async () => {
  init_eventEmitter();
  init_BuildConfig();
  await __promiseAll([
    init_native(),
    init_BrowserView(),
    init_Utils()
  ]);
  buildConfig3 = await BuildConfig.get();
  defaultOptions2 = {
    title: "Electrobun",
    frame: {
      x: 0,
      y: 0,
      width: 800,
      height: 600
    },
    url: "https://electrobun.dev",
    html: null,
    preload: null,
    renderer: buildConfig3.defaultRenderer,
    titleBarStyle: "default",
    transparent: false,
    navigationRules: null,
    sandbox: false
  };
  BrowserWindowMap = {};
  eventEmitter_default.on("close", (event) => {
    const windowId = event.data.id;
    delete BrowserWindowMap[windowId];
    for (const view of BrowserView.getAll()) {
      if (view.windowId === windowId) {
        view.remove();
      }
    }
    const exitOnLastWindowClosed = buildConfig3.runtime?.exitOnLastWindowClosed ?? true;
    if (exitOnLastWindowClosed && Object.keys(BrowserWindowMap).length === 0) {
      quit();
    }
  });
});

// node_modules/abbrev/lib/index.js
var require_lib = __commonJS((exports, module) => {
  module.exports = abbrev;
  function abbrev(...args) {
    let list = args;
    if (args.length === 1 && (Array.isArray(args[0]) || typeof args[0] === "string")) {
      list = [].concat(args[0]);
    }
    for (let i = 0, l = list.length;i < l; i++) {
      list[i] = typeof list[i] === "string" ? list[i] : String(list[i]);
    }
    list = list.sort(lexSort);
    const abbrevs = {};
    let prev = "";
    for (let ii = 0, ll = list.length;ii < ll; ii++) {
      const current = list[ii];
      const next = list[ii + 1] || "";
      let nextMatches = true;
      let prevMatches = true;
      if (current === next) {
        continue;
      }
      let j = 0;
      const cl = current.length;
      for (;j < cl; j++) {
        const curChar = current.charAt(j);
        nextMatches = nextMatches && curChar === next.charAt(j);
        prevMatches = prevMatches && curChar === prev.charAt(j);
        if (!nextMatches && !prevMatches) {
          j++;
          break;
        }
      }
      prev = current;
      if (j === cl) {
        abbrevs[current] = current;
        continue;
      }
      for (let a = current.slice(0, j);j <= cl; j++) {
        abbrevs[a] = current;
        a += current.charAt(j);
      }
    }
    return abbrevs;
  }
  function lexSort(a, b) {
    return a === b ? 0 : a > b ? 1 : -1;
  }
});

// node_modules/nopt/lib/debug.js
var require_debug = __commonJS((exports, module) => {
  module.exports = process.env.DEBUG_NOPT || process.env.NOPT_DEBUG ? (...a) => console.error(...a) : () => {};
});

// node_modules/nopt/lib/type-defs.js
var require_type_defs = __commonJS((exports, module) => {
  var url = __require("url");
  var path = __require("path");
  var Stream = __require("stream").Stream;
  var os = __require("os");
  var debug = require_debug();
  function validateString(data, k, val) {
    data[k] = String(val);
  }
  function validatePath(data, k, val) {
    if (val === true) {
      return false;
    }
    if (val === null) {
      return true;
    }
    val = String(val);
    const isWin = process.platform === "win32";
    const homePattern = isWin ? /^~(\/|\\)/ : /^~\//;
    const home2 = os.homedir();
    if (home2 && val.match(homePattern)) {
      data[k] = path.resolve(home2, val.slice(2));
    } else {
      data[k] = path.resolve(val);
    }
    return true;
  }
  function validateNumber(data, k, val) {
    debug("validate Number %j %j %j", k, val, isNaN(val));
    if (isNaN(val)) {
      return false;
    }
    data[k] = +val;
  }
  function validateDate(data, k, val) {
    const s = Date.parse(val);
    debug("validate Date %j %j %j", k, val, s);
    if (isNaN(s)) {
      return false;
    }
    data[k] = new Date(val);
  }
  function validateBoolean(data, k, val) {
    if (typeof val === "string") {
      if (!isNaN(val)) {
        val = !!+val;
      } else if (val === "null" || val === "false") {
        val = false;
      } else {
        val = true;
      }
    } else {
      val = !!val;
    }
    data[k] = val;
  }
  function validateUrl(data, k, val) {
    val = url.parse(String(val));
    if (!val.host) {
      return false;
    }
    data[k] = val.href;
  }
  function validateStream(data, k, val) {
    if (!(val instanceof Stream)) {
      return false;
    }
    data[k] = val;
  }
  module.exports = {
    String: { type: String, validate: validateString },
    Boolean: { type: Boolean, validate: validateBoolean },
    url: { type: url, validate: validateUrl },
    Number: { type: Number, validate: validateNumber },
    path: { type: path, validate: validatePath },
    Stream: { type: Stream, validate: validateStream },
    Date: { type: Date, validate: validateDate },
    Array: { type: Array }
  };
});

// node_modules/nopt/lib/nopt-lib.js
var require_nopt_lib = __commonJS((exports, module) => {
  var abbrev = require_lib();
  var debug = require_debug();
  var defaultTypeDefs = require_type_defs();
  var hasOwn = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  var getType = (k, { types, dynamicTypes }) => {
    let hasType = hasOwn(types, k);
    let type = types[k];
    if (!hasType && typeof dynamicTypes === "function") {
      const matchedType = dynamicTypes(k);
      if (matchedType !== undefined) {
        type = matchedType;
        hasType = true;
      }
    }
    return [hasType, type];
  };
  var isTypeDef = (type, def) => def && type === def;
  var hasTypeDef = (type, def) => def && type.indexOf(def) !== -1;
  var doesNotHaveTypeDef = (type, def) => def && !hasTypeDef(type, def);
  function nopt(args, {
    types,
    shorthands,
    typeDefs,
    invalidHandler,
    unknownHandler,
    abbrevHandler,
    typeDefault,
    dynamicTypes
  } = {}) {
    debug(types, shorthands, args, typeDefs);
    const data = {};
    const argv = {
      remain: [],
      cooked: args,
      original: args.slice(0)
    };
    parse(args, data, argv.remain, {
      typeDefs,
      types,
      dynamicTypes,
      shorthands,
      unknownHandler,
      abbrevHandler
    });
    clean(data, { types, dynamicTypes, typeDefs, invalidHandler, typeDefault });
    data.argv = argv;
    Object.defineProperty(data.argv, "toString", {
      value: function() {
        return this.original.map(JSON.stringify).join(" ");
      },
      enumerable: false
    });
    return data;
  }
  function clean(data, {
    types = {},
    typeDefs = {},
    dynamicTypes,
    invalidHandler,
    typeDefault
  } = {}) {
    const StringType = typeDefs.String?.type;
    const NumberType = typeDefs.Number?.type;
    const ArrayType = typeDefs.Array?.type;
    const BooleanType = typeDefs.Boolean?.type;
    const DateType = typeDefs.Date?.type;
    const hasTypeDefault = typeof typeDefault !== "undefined";
    if (!hasTypeDefault) {
      typeDefault = [false, true, null];
      if (StringType) {
        typeDefault.push(StringType);
      }
      if (ArrayType) {
        typeDefault.push(ArrayType);
      }
    }
    const remove = {};
    Object.keys(data).forEach((k) => {
      if (k === "argv") {
        return;
      }
      let val = data[k];
      debug("val=%j", val);
      const isArray = Array.isArray(val);
      let [hasType, rawType] = getType(k, { types, dynamicTypes });
      let type = rawType;
      if (!isArray) {
        val = [val];
      }
      if (!type) {
        type = typeDefault;
      }
      if (isTypeDef(type, ArrayType)) {
        type = typeDefault.concat(ArrayType);
      }
      if (!Array.isArray(type)) {
        type = [type];
      }
      debug("val=%j", val);
      debug("types=", type);
      val = val.map((v) => {
        if (typeof v === "string") {
          debug("string %j", v);
          v = v.trim();
          if (v === "null" && ~type.indexOf(null) || v === "true" && (~type.indexOf(true) || hasTypeDef(type, BooleanType)) || v === "false" && (~type.indexOf(false) || hasTypeDef(type, BooleanType))) {
            v = JSON.parse(v);
            debug("jsonable %j", v);
          } else if (hasTypeDef(type, NumberType) && !isNaN(v)) {
            debug("convert to number", v);
            v = +v;
          } else if (hasTypeDef(type, DateType) && !isNaN(Date.parse(v))) {
            debug("convert to date", v);
            v = new Date(v);
          }
        }
        if (!hasType) {
          if (!hasTypeDefault) {
            return v;
          }
          rawType = typeDefault;
        }
        if (v === false && ~type.indexOf(null) && !(~type.indexOf(false) || hasTypeDef(type, BooleanType))) {
          v = null;
        }
        const d = {};
        d[k] = v;
        debug("prevalidated val", d, v, rawType);
        if (!validate(d, k, v, rawType, { typeDefs })) {
          if (invalidHandler) {
            invalidHandler(k, v, rawType, data);
          } else if (invalidHandler !== false) {
            debug("invalid: " + k + "=" + v, rawType);
          }
          return remove;
        }
        debug("validated v", d, v, rawType);
        return d[k];
      }).filter((v) => v !== remove);
      if (!val.length && doesNotHaveTypeDef(type, ArrayType)) {
        debug("VAL HAS NO LENGTH, DELETE IT", val, k, type.indexOf(ArrayType));
        delete data[k];
      } else if (isArray) {
        debug(isArray, data[k], val);
        data[k] = val;
      } else {
        data[k] = val[0];
      }
      debug("k=%s val=%j", k, val, data[k]);
    });
  }
  function validate(data, k, val, type, { typeDefs } = {}) {
    const ArrayType = typeDefs?.Array?.type;
    if (Array.isArray(type)) {
      for (let i = 0, l = type.length;i < l; i++) {
        if (isTypeDef(type[i], ArrayType)) {
          continue;
        }
        if (validate(data, k, val, type[i], { typeDefs })) {
          return true;
        }
      }
      delete data[k];
      return false;
    }
    if (isTypeDef(type, ArrayType)) {
      return true;
    }
    if (type !== type) {
      debug("Poison NaN", k, val, type);
      delete data[k];
      return false;
    }
    if (val === type) {
      debug("Explicitly allowed %j", val);
      data[k] = val;
      return true;
    }
    let ok = false;
    const types = Object.keys(typeDefs);
    for (let i = 0, l = types.length;i < l; i++) {
      debug("test type %j %j %j", k, val, types[i]);
      const t = typeDefs[types[i]];
      if (t && (type && type.name && t.type && t.type.name ? type.name === t.type.name : type === t.type)) {
        const d = {};
        ok = t.validate(d, k, val) !== false;
        val = d[k];
        if (ok) {
          data[k] = val;
          break;
        }
      }
    }
    debug("OK? %j (%j %j %j)", ok, k, val, types[types.length - 1]);
    if (!ok) {
      delete data[k];
    }
    return ok;
  }
  function parse(args, data, remain, {
    types = {},
    typeDefs = {},
    shorthands = {},
    dynamicTypes,
    unknownHandler,
    abbrevHandler
  } = {}) {
    const StringType = typeDefs.String?.type;
    const NumberType = typeDefs.Number?.type;
    const ArrayType = typeDefs.Array?.type;
    const BooleanType = typeDefs.Boolean?.type;
    debug("parse", args, data, remain);
    const abbrevs = abbrev(Object.keys(types));
    debug("abbrevs=%j", abbrevs);
    const shortAbbr = abbrev(Object.keys(shorthands));
    for (let i = 0;i < args.length; i++) {
      let arg = args[i];
      debug("arg", arg);
      if (arg.match(/^-{2,}$/)) {
        remain.push.apply(remain, args.slice(i + 1));
        args[i] = "--";
        break;
      }
      let hadEq = false;
      if (arg.charAt(0) === "-" && arg.length > 1) {
        const at = arg.indexOf("=");
        if (at > -1) {
          hadEq = true;
          const v = arg.slice(at + 1);
          arg = arg.slice(0, at);
          args.splice(i, 1, arg, v);
        }
        const shRes = resolveShort(arg, shortAbbr, abbrevs, { shorthands, abbrevHandler });
        debug("arg=%j shRes=%j", arg, shRes);
        if (shRes) {
          args.splice.apply(args, [i, 1].concat(shRes));
          if (arg !== shRes[0]) {
            i--;
            continue;
          }
        }
        arg = arg.replace(/^-+/, "");
        let no = null;
        while (arg.toLowerCase().indexOf("no-") === 0) {
          no = !no;
          arg = arg.slice(3);
        }
        if (abbrevs[arg] && abbrevs[arg] !== arg) {
          if (abbrevHandler) {
            abbrevHandler(arg, abbrevs[arg]);
          } else if (abbrevHandler !== false) {
            debug(`abbrev: ${arg} -> ${abbrevs[arg]}`);
          }
          arg = abbrevs[arg];
        }
        let [hasType, argType] = getType(arg, { types, dynamicTypes });
        let isTypeArray = Array.isArray(argType);
        if (isTypeArray && argType.length === 1) {
          isTypeArray = false;
          argType = argType[0];
        }
        let isArray = isTypeDef(argType, ArrayType) || isTypeArray && hasTypeDef(argType, ArrayType);
        if (!hasType && hasOwn(data, arg)) {
          if (!Array.isArray(data[arg])) {
            data[arg] = [data[arg]];
          }
          isArray = true;
        }
        let val;
        let la = args[i + 1];
        const isBool = typeof no === "boolean" || isTypeDef(argType, BooleanType) || isTypeArray && hasTypeDef(argType, BooleanType) || typeof argType === "undefined" && !hadEq || la === "false" && (argType === null || isTypeArray && ~argType.indexOf(null));
        if (typeof argType === "undefined") {
          const hangingLa = !hadEq && la && !la?.startsWith("-") && !["true", "false"].includes(la);
          if (unknownHandler) {
            if (hangingLa) {
              unknownHandler(arg, la);
            } else {
              unknownHandler(arg);
            }
          } else if (unknownHandler !== false) {
            debug(`unknown: ${arg}`);
            if (hangingLa) {
              debug(`unknown: ${la} parsed as normal opt`);
            }
          }
        }
        if (isBool) {
          val = !no;
          if (la === "true" || la === "false") {
            val = JSON.parse(la);
            la = null;
            if (no) {
              val = !val;
            }
            i++;
          }
          if (isTypeArray && la) {
            if (~argType.indexOf(la)) {
              val = la;
              i++;
            } else if (la === "null" && ~argType.indexOf(null)) {
              val = null;
              i++;
            } else if (!la.match(/^-{2,}[^-]/) && !isNaN(la) && hasTypeDef(argType, NumberType)) {
              val = +la;
              i++;
            } else if (!la.match(/^-[^-]/) && hasTypeDef(argType, StringType)) {
              val = la;
              i++;
            }
          }
          if (isArray) {
            (data[arg] = data[arg] || []).push(val);
          } else {
            data[arg] = val;
          }
          continue;
        }
        if (isTypeDef(argType, StringType)) {
          if (la === undefined) {
            la = "";
          } else if (la.match(/^-{1,2}[^-]+/)) {
            la = "";
            i--;
          }
        }
        if (la && la.match(/^-{2,}$/)) {
          la = undefined;
          i--;
        }
        val = la === undefined ? true : la;
        if (isArray) {
          (data[arg] = data[arg] || []).push(val);
        } else {
          data[arg] = val;
        }
        i++;
        continue;
      }
      remain.push(arg);
    }
  }
  var SINGLES = Symbol("singles");
  var singleCharacters = (arg, shorthands) => {
    let singles = shorthands[SINGLES];
    if (!singles) {
      singles = Object.keys(shorthands).filter((s) => s.length === 1).reduce((l, r) => {
        l[r] = true;
        return l;
      }, {});
      shorthands[SINGLES] = singles;
      debug("shorthand singles", singles);
    }
    const chrs = arg.split("").filter((c) => singles[c]);
    return chrs.join("") === arg ? chrs : null;
  };
  function resolveShort(arg, ...rest) {
    const { abbrevHandler, types = {}, shorthands = {} } = rest.length ? rest.pop() : {};
    const shortAbbr = rest[0] ?? abbrev(Object.keys(shorthands));
    const abbrevs = rest[1] ?? abbrev(Object.keys(types));
    arg = arg.replace(/^-+/, "");
    if (abbrevs[arg] === arg) {
      return null;
    }
    if (shorthands[arg]) {
      if (shorthands[arg] && !Array.isArray(shorthands[arg])) {
        shorthands[arg] = shorthands[arg].split(/\s+/);
      }
      return shorthands[arg];
    }
    const chrs = singleCharacters(arg, shorthands);
    if (chrs) {
      return chrs.map((c) => shorthands[c]).reduce((l, r) => l.concat(r), []);
    }
    if (abbrevs[arg] && !shorthands[arg]) {
      return null;
    }
    if (shortAbbr[arg]) {
      if (abbrevHandler) {
        abbrevHandler(arg, shortAbbr[arg]);
      } else if (abbrevHandler !== false) {
        debug(`abbrev: ${arg} -> ${shortAbbr[arg]}`);
      }
      arg = shortAbbr[arg];
    }
    if (shorthands[arg] && !Array.isArray(shorthands[arg])) {
      shorthands[arg] = shorthands[arg].split(/\s+/);
    }
    return shorthands[arg];
  }
  module.exports = {
    nopt,
    clean,
    parse,
    validate,
    resolveShort,
    typeDefs: defaultTypeDefs
  };
});

// node_modules/nopt/lib/nopt.js
var require_nopt = __commonJS((exports, module) => {
  var lib = require_nopt_lib();
  var defaultTypeDefs = require_type_defs();
  module.exports = exports = nopt;
  exports.clean = clean;
  exports.typeDefs = defaultTypeDefs;
  exports.lib = lib;
  function nopt(types, shorthands, args = process.argv, slice = 2) {
    return lib.nopt(args.slice(slice), {
      types: types || {},
      shorthands: shorthands || {},
      typeDefs: exports.typeDefs,
      invalidHandler: exports.invalidHandler,
      unknownHandler: exports.unknownHandler,
      abbrevHandler: exports.abbrevHandler
    });
  }
  function clean(data, types, typeDefs = exports.typeDefs) {
    return lib.clean(data, {
      types: types || {},
      typeDefs,
      invalidHandler: exports.invalidHandler,
      unknownHandler: exports.unknownHandler,
      abbrevHandler: exports.abbrevHandler
    });
  }
});

// node_modules/consola/dist/core.cjs
var require_core = __commonJS((exports) => {
  var LogLevels = {
    silent: Number.NEGATIVE_INFINITY,
    fatal: 0,
    error: 0,
    warn: 1,
    log: 2,
    info: 3,
    success: 3,
    fail: 3,
    ready: 3,
    start: 3,
    box: 3,
    debug: 4,
    trace: 5,
    verbose: Number.POSITIVE_INFINITY
  };
  var LogTypes = {
    silent: {
      level: -1
    },
    fatal: {
      level: LogLevels.fatal
    },
    error: {
      level: LogLevels.error
    },
    warn: {
      level: LogLevels.warn
    },
    log: {
      level: LogLevels.log
    },
    info: {
      level: LogLevels.info
    },
    success: {
      level: LogLevels.success
    },
    fail: {
      level: LogLevels.fail
    },
    ready: {
      level: LogLevels.info
    },
    start: {
      level: LogLevels.info
    },
    box: {
      level: LogLevels.info
    },
    debug: {
      level: LogLevels.debug
    },
    trace: {
      level: LogLevels.trace
    },
    verbose: {
      level: LogLevels.verbose
    }
  };
  function isPlainObject$1(value) {
    if (value === null || typeof value !== "object") {
      return false;
    }
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== null && prototype !== Object.prototype && Object.getPrototypeOf(prototype) !== null) {
      return false;
    }
    if (Symbol.iterator in value) {
      return false;
    }
    if (Symbol.toStringTag in value) {
      return Object.prototype.toString.call(value) === "[object Module]";
    }
    return true;
  }
  function _defu(baseObject, defaults, namespace = ".", merger) {
    if (!isPlainObject$1(defaults)) {
      return _defu(baseObject, {}, namespace, merger);
    }
    const object = Object.assign({}, defaults);
    for (const key in baseObject) {
      if (key === "__proto__" || key === "constructor") {
        continue;
      }
      const value = baseObject[key];
      if (value === null || value === undefined) {
        continue;
      }
      if (merger && merger(object, key, value, namespace)) {
        continue;
      }
      if (Array.isArray(value) && Array.isArray(object[key])) {
        object[key] = [...value, ...object[key]];
      } else if (isPlainObject$1(value) && isPlainObject$1(object[key])) {
        object[key] = _defu(value, object[key], (namespace ? `${namespace}.` : "") + key.toString(), merger);
      } else {
        object[key] = value;
      }
    }
    return object;
  }
  function createDefu(merger) {
    return (...arguments_) => arguments_.reduce((p, c) => _defu(p, c, "", merger), {});
  }
  var defu = createDefu();
  function isPlainObject(obj) {
    return Object.prototype.toString.call(obj) === "[object Object]";
  }
  function isLogObj(arg) {
    if (!isPlainObject(arg)) {
      return false;
    }
    if (!arg.message && !arg.args) {
      return false;
    }
    if (arg.stack) {
      return false;
    }
    return true;
  }
  var paused = false;
  var queue = [];

  class Consola {
    options;
    _lastLog;
    _mockFn;
    constructor(options = {}) {
      const types = options.types || LogTypes;
      this.options = defu({
        ...options,
        defaults: { ...options.defaults },
        level: _normalizeLogLevel(options.level, types),
        reporters: [...options.reporters || []]
      }, {
        types: LogTypes,
        throttle: 1000,
        throttleMin: 5,
        formatOptions: {
          date: true,
          colors: false,
          compact: true
        }
      });
      for (const type in types) {
        const defaults = {
          type,
          ...this.options.defaults,
          ...types[type]
        };
        this[type] = this._wrapLogFn(defaults);
        this[type].raw = this._wrapLogFn(defaults, true);
      }
      if (this.options.mockFn) {
        this.mockTypes();
      }
      this._lastLog = {};
    }
    get level() {
      return this.options.level;
    }
    set level(level) {
      this.options.level = _normalizeLogLevel(level, this.options.types, this.options.level);
    }
    prompt(message, opts) {
      if (!this.options.prompt) {
        throw new Error("prompt is not supported!");
      }
      return this.options.prompt(message, opts);
    }
    create(options) {
      const instance = new Consola({
        ...this.options,
        ...options
      });
      if (this._mockFn) {
        instance.mockTypes(this._mockFn);
      }
      return instance;
    }
    withDefaults(defaults) {
      return this.create({
        ...this.options,
        defaults: {
          ...this.options.defaults,
          ...defaults
        }
      });
    }
    withTag(tag) {
      return this.withDefaults({
        tag: this.options.defaults.tag ? this.options.defaults.tag + ":" + tag : tag
      });
    }
    addReporter(reporter) {
      this.options.reporters.push(reporter);
      return this;
    }
    removeReporter(reporter) {
      if (reporter) {
        const i = this.options.reporters.indexOf(reporter);
        if (i !== -1) {
          return this.options.reporters.splice(i, 1);
        }
      } else {
        this.options.reporters.splice(0);
      }
      return this;
    }
    setReporters(reporters) {
      this.options.reporters = Array.isArray(reporters) ? reporters : [reporters];
      return this;
    }
    wrapAll() {
      this.wrapConsole();
      this.wrapStd();
    }
    restoreAll() {
      this.restoreConsole();
      this.restoreStd();
    }
    wrapConsole() {
      for (const type in this.options.types) {
        if (!console["__" + type]) {
          console["__" + type] = console[type];
        }
        console[type] = this[type].raw;
      }
    }
    restoreConsole() {
      for (const type in this.options.types) {
        if (console["__" + type]) {
          console[type] = console["__" + type];
          delete console["__" + type];
        }
      }
    }
    wrapStd() {
      this._wrapStream(this.options.stdout, "log");
      this._wrapStream(this.options.stderr, "log");
    }
    _wrapStream(stream, type) {
      if (!stream) {
        return;
      }
      if (!stream.__write) {
        stream.__write = stream.write;
      }
      stream.write = (data) => {
        this[type].raw(String(data).trim());
      };
    }
    restoreStd() {
      this._restoreStream(this.options.stdout);
      this._restoreStream(this.options.stderr);
    }
    _restoreStream(stream) {
      if (!stream) {
        return;
      }
      if (stream.__write) {
        stream.write = stream.__write;
        delete stream.__write;
      }
    }
    pauseLogs() {
      paused = true;
    }
    resumeLogs() {
      paused = false;
      const _queue = queue.splice(0);
      for (const item of _queue) {
        item[0]._logFn(item[1], item[2]);
      }
    }
    mockTypes(mockFn) {
      const _mockFn = mockFn || this.options.mockFn;
      this._mockFn = _mockFn;
      if (typeof _mockFn !== "function") {
        return;
      }
      for (const type in this.options.types) {
        this[type] = _mockFn(type, this.options.types[type]) || this[type];
        this[type].raw = this[type];
      }
    }
    _wrapLogFn(defaults, isRaw) {
      return (...args) => {
        if (paused) {
          queue.push([this, defaults, args, isRaw]);
          return;
        }
        return this._logFn(defaults, args, isRaw);
      };
    }
    _logFn(defaults, args, isRaw) {
      if ((defaults.level || 0) > this.level) {
        return false;
      }
      const logObj = {
        date: /* @__PURE__ */ new Date,
        args: [],
        ...defaults,
        level: _normalizeLogLevel(defaults.level, this.options.types)
      };
      if (!isRaw && args.length === 1 && isLogObj(args[0])) {
        Object.assign(logObj, args[0]);
      } else {
        logObj.args = [...args];
      }
      if (logObj.message) {
        logObj.args.unshift(logObj.message);
        delete logObj.message;
      }
      if (logObj.additional) {
        if (!Array.isArray(logObj.additional)) {
          logObj.additional = logObj.additional.split(`
`);
        }
        logObj.args.push(`
` + logObj.additional.join(`
`));
        delete logObj.additional;
      }
      logObj.type = typeof logObj.type === "string" ? logObj.type.toLowerCase() : "log";
      logObj.tag = typeof logObj.tag === "string" ? logObj.tag : "";
      const resolveLog = (newLog = false) => {
        const repeated = (this._lastLog.count || 0) - this.options.throttleMin;
        if (this._lastLog.object && repeated > 0) {
          const args2 = [...this._lastLog.object.args];
          if (repeated > 1) {
            args2.push(`(repeated ${repeated} times)`);
          }
          this._log({ ...this._lastLog.object, args: args2 });
          this._lastLog.count = 1;
        }
        if (newLog) {
          this._lastLog.object = logObj;
          this._log(logObj);
        }
      };
      clearTimeout(this._lastLog.timeout);
      const diffTime = this._lastLog.time && logObj.date ? logObj.date.getTime() - this._lastLog.time.getTime() : 0;
      this._lastLog.time = logObj.date;
      if (diffTime < this.options.throttle) {
        try {
          const serializedLog = JSON.stringify([
            logObj.type,
            logObj.tag,
            logObj.args
          ]);
          const isSameLog = this._lastLog.serialized === serializedLog;
          this._lastLog.serialized = serializedLog;
          if (isSameLog) {
            this._lastLog.count = (this._lastLog.count || 0) + 1;
            if (this._lastLog.count > this.options.throttleMin) {
              this._lastLog.timeout = setTimeout(resolveLog, this.options.throttle);
              return;
            }
          }
        } catch {}
      }
      resolveLog(true);
    }
    _log(logObj) {
      for (const reporter of this.options.reporters) {
        reporter.log(logObj, {
          options: this.options
        });
      }
    }
  }
  function _normalizeLogLevel(input, types = {}, defaultLevel = 3) {
    if (input === undefined) {
      return defaultLevel;
    }
    if (typeof input === "number") {
      return input;
    }
    if (types[input] && types[input].level !== undefined) {
      return types[input].level;
    }
    return defaultLevel;
  }
  Consola.prototype.add = Consola.prototype.addReporter;
  Consola.prototype.remove = Consola.prototype.removeReporter;
  Consola.prototype.clear = Consola.prototype.removeReporter;
  Consola.prototype.withScope = Consola.prototype.withTag;
  Consola.prototype.mock = Consola.prototype.mockTypes;
  Consola.prototype.pause = Consola.prototype.pauseLogs;
  Consola.prototype.resume = Consola.prototype.resumeLogs;
  function createConsola(options = {}) {
    return new Consola(options);
  }
  exports.Consola = Consola;
  exports.LogLevels = LogLevels;
  exports.LogTypes = LogTypes;
  exports.createConsola = createConsola;
});

// node_modules/consola/dist/shared/consola.DCGIlDNP.cjs
var require_consola_DCGIlDNP = __commonJS((exports) => {
  var node_util = __require("util");
  var node_path = __require("path");
  function parseStack(stack, message) {
    const cwd = process.cwd() + node_path.sep;
    const lines = stack.split(`
`).splice(message.split(`
`).length).map((l) => l.trim().replace("file://", "").replace(cwd, ""));
    return lines;
  }
  function writeStream(data, stream) {
    const write = stream.__write || stream.write;
    return write.call(stream, data);
  }
  var bracket = (x) => x ? `[${x}]` : "";

  class BasicReporter {
    formatStack(stack, message, opts) {
      const indent = "  ".repeat((opts?.errorLevel || 0) + 1);
      return indent + parseStack(stack, message).join(`
${indent}`);
    }
    formatError(err, opts) {
      const message = err.message ?? node_util.formatWithOptions(opts, err);
      const stack = err.stack ? this.formatStack(err.stack, message, opts) : "";
      const level = opts?.errorLevel || 0;
      const causedPrefix = level > 0 ? `${"  ".repeat(level)}[cause]: ` : "";
      const causedError = err.cause ? `

` + this.formatError(err.cause, { ...opts, errorLevel: level + 1 }) : "";
      return causedPrefix + message + `
` + stack + causedError;
    }
    formatArgs(args, opts) {
      const _args = args.map((arg) => {
        if (arg && typeof arg.stack === "string") {
          return this.formatError(arg, opts);
        }
        return arg;
      });
      return node_util.formatWithOptions(opts, ..._args);
    }
    formatDate(date, opts) {
      return opts.date ? date.toLocaleTimeString() : "";
    }
    filterAndJoin(arr) {
      return arr.filter(Boolean).join(" ");
    }
    formatLogObj(logObj, opts) {
      const message = this.formatArgs(logObj.args, opts);
      if (logObj.type === "box") {
        return `
` + [
          bracket(logObj.tag),
          logObj.title && logObj.title,
          ...message.split(`
`)
        ].filter(Boolean).map((l) => " > " + l).join(`
`) + `
`;
      }
      return this.filterAndJoin([
        bracket(logObj.type),
        bracket(logObj.tag),
        message
      ]);
    }
    log(logObj, ctx) {
      const line = this.formatLogObj(logObj, {
        columns: ctx.options.stdout.columns || 0,
        ...ctx.options.formatOptions
      });
      return writeStream(line + `
`, logObj.level < 2 ? ctx.options.stderr || process.stderr : ctx.options.stdout || process.stdout);
    }
  }
  exports.BasicReporter = BasicReporter;
  exports.parseStack = parseStack;
});

// node_modules/consola/dist/basic.cjs
var require_basic = __commonJS((exports) => {
  Object.defineProperty(exports, "__esModule", { value: true });
  var core = require_core();
  var basic = require_consola_DCGIlDNP();
  __require("util");
  __require("path");
  function createConsola(options = {}) {
    let level = core.LogLevels.info;
    if (process.env.CONSOLA_LEVEL) {
      level = Number.parseInt(process.env.CONSOLA_LEVEL) ?? level;
    }
    const consola2 = core.createConsola({
      level,
      defaults: { level },
      stdout: process.stdout,
      stderr: process.stderr,
      reporters: options.reporters || [new basic.BasicReporter],
      ...options
    });
    return consola2;
  }
  var consola = createConsola();
  exports.Consola = core.Consola;
  exports.LogLevels = core.LogLevels;
  exports.LogTypes = core.LogTypes;
  exports.consola = consola;
  exports.createConsola = createConsola;
  exports.default = consola;
});

// node_modules/@mapbox/node-pre-gyp/lib/util/log.js
var require_log = __commonJS((exports, module) => {
  var { createConsola } = require_basic();
  var log = createConsola({ stdout: process.stderr });
  module.exports = exports = log;
});

// node_modules/@mapbox/node-pre-gyp/lib/util/napi.js
var require_napi = __commonJS((exports, module) => {
  var fs = __require("fs");
  module.exports = exports;
  var versionArray = process.version.substr(1).replace(/-.*$/, "").split(".").map((item) => {
    return +item;
  });
  var napi_multiple_commands = [
    "build",
    "clean",
    "configure",
    "package",
    "publish",
    "reveal",
    "testbinary",
    "testpackage",
    "unpublish"
  ];
  var napi_build_version_tag = "napi_build_version=";
  module.exports.get_napi_version = function() {
    let version = process.versions.napi;
    if (!version) {
      if (versionArray[0] === 9 && versionArray[1] >= 3)
        version = 2;
      else if (versionArray[0] === 8)
        version = 1;
    }
    return version;
  };
  module.exports.get_napi_version_as_string = function(target) {
    const version = module.exports.get_napi_version(target);
    return version ? "" + version : "";
  };
  module.exports.validate_package_json = function(package_json, opts) {
    const binary = package_json.binary;
    const module_path_ok = pathOK(binary.module_path);
    const remote_path_ok = pathOK(binary.remote_path);
    const package_name_ok = pathOK(binary.package_name);
    const napi_build_versions = module.exports.get_napi_build_versions(package_json, opts, true);
    const napi_build_versions_raw = module.exports.get_napi_build_versions_raw(package_json);
    if (napi_build_versions) {
      napi_build_versions.forEach((napi_build_version) => {
        if (!(parseInt(napi_build_version, 10) === napi_build_version && napi_build_version > 0)) {
          throw new Error("All values specified in napi_versions must be positive integers.");
        }
      });
    }
    if (napi_build_versions && (!module_path_ok || !remote_path_ok && !package_name_ok)) {
      throw new Error("When napi_versions is specified; module_path and either remote_path or " + "package_name must contain the substitution string '{napi_build_version}`.");
    }
    if ((module_path_ok || remote_path_ok || package_name_ok) && !napi_build_versions_raw) {
      throw new Error("When the substitution string '{napi_build_version}` is specified in " + "module_path, remote_path, or package_name; napi_versions must also be specified.");
    }
    if (napi_build_versions && !module.exports.get_best_napi_build_version(package_json, opts) && module.exports.build_napi_only(package_json)) {
      throw new Error("The Node-API version of this Node instance is " + module.exports.get_napi_version(opts ? opts.target : undefined) + ". " + "This module supports Node-API version(s) " + module.exports.get_napi_build_versions_raw(package_json) + ". " + "This Node instance cannot run this module.");
    }
    if (napi_build_versions_raw && !napi_build_versions && module.exports.build_napi_only(package_json)) {
      throw new Error("The Node-API version of this Node instance is " + module.exports.get_napi_version(opts ? opts.target : undefined) + ". " + "This module supports Node-API version(s) " + module.exports.get_napi_build_versions_raw(package_json) + ". " + "This Node instance cannot run this module.");
    }
  };
  function pathOK(path) {
    return path && (path.indexOf("{napi_build_version}") !== -1 || path.indexOf("{node_napi_label}") !== -1);
  }
  module.exports.expand_commands = function(package_json, opts, commands) {
    const expanded_commands = [];
    const napi_build_versions = module.exports.get_napi_build_versions(package_json, opts);
    commands.forEach((command) => {
      if (napi_build_versions && command.name === "install") {
        const napi_build_version = module.exports.get_best_napi_build_version(package_json, opts);
        const args = napi_build_version ? [napi_build_version_tag + napi_build_version] : [];
        expanded_commands.push({ name: command.name, args });
      } else if (napi_build_versions && napi_multiple_commands.indexOf(command.name) !== -1) {
        napi_build_versions.forEach((napi_build_version) => {
          const args = command.args.slice();
          args.push(napi_build_version_tag + napi_build_version);
          expanded_commands.push({ name: command.name, args });
        });
      } else {
        expanded_commands.push(command);
      }
    });
    return expanded_commands;
  };
  module.exports.get_napi_build_versions = function(package_json, opts, warnings) {
    const log = require_log();
    let napi_build_versions = [];
    const supported_napi_version = module.exports.get_napi_version(opts ? opts.target : undefined);
    if (package_json.binary && package_json.binary.napi_versions) {
      package_json.binary.napi_versions.forEach((napi_version) => {
        const duplicated = napi_build_versions.indexOf(napi_version) !== -1;
        if (!duplicated && supported_napi_version && napi_version <= supported_napi_version) {
          napi_build_versions.push(napi_version);
        } else if (warnings && !duplicated && supported_napi_version) {
          log.info("This Node instance does not support builds for Node-API version", napi_version);
        }
      });
    }
    if (opts && opts["build-latest-napi-version-only"]) {
      let latest_version = 0;
      napi_build_versions.forEach((napi_version) => {
        if (napi_version > latest_version)
          latest_version = napi_version;
      });
      napi_build_versions = latest_version ? [latest_version] : [];
    }
    return napi_build_versions.length ? napi_build_versions : undefined;
  };
  module.exports.get_napi_build_versions_raw = function(package_json) {
    const napi_build_versions = [];
    if (package_json.binary && package_json.binary.napi_versions) {
      package_json.binary.napi_versions.forEach((napi_version) => {
        if (napi_build_versions.indexOf(napi_version) === -1) {
          napi_build_versions.push(napi_version);
        }
      });
    }
    return napi_build_versions.length ? napi_build_versions : undefined;
  };
  module.exports.get_command_arg = function(napi_build_version) {
    return napi_build_version_tag + napi_build_version;
  };
  module.exports.get_napi_build_version_from_command_args = function(command_args) {
    for (let i = 0;i < command_args.length; i++) {
      const arg = command_args[i];
      if (arg.indexOf(napi_build_version_tag) === 0) {
        return parseInt(arg.substr(napi_build_version_tag.length), 10);
      }
    }
    return;
  };
  module.exports.swap_build_dir_out = function(napi_build_version) {
    if (napi_build_version) {
      fs.rmSync(module.exports.get_build_dir(napi_build_version), { recursive: true, force: true });
      fs.renameSync("build", module.exports.get_build_dir(napi_build_version));
    }
  };
  module.exports.swap_build_dir_in = function(napi_build_version) {
    if (napi_build_version) {
      fs.rmSync("build", { recursive: true, force: true });
      fs.renameSync(module.exports.get_build_dir(napi_build_version), "build");
    }
  };
  module.exports.get_build_dir = function(napi_build_version) {
    return "build-tmp-napi-v" + napi_build_version;
  };
  module.exports.get_best_napi_build_version = function(package_json, opts) {
    let best_napi_build_version = 0;
    const napi_build_versions = module.exports.get_napi_build_versions(package_json, opts);
    if (napi_build_versions) {
      const our_napi_version = module.exports.get_napi_version(opts ? opts.target : undefined);
      napi_build_versions.forEach((napi_build_version) => {
        if (napi_build_version > best_napi_build_version && napi_build_version <= our_napi_version) {
          best_napi_build_version = napi_build_version;
        }
      });
    }
    return best_napi_build_version === 0 ? undefined : best_napi_build_version;
  };
  module.exports.build_napi_only = function(package_json) {
    return package_json.binary && package_json.binary.package_name && package_json.binary.package_name.indexOf("{node_napi_label}") === -1;
  };
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/internal/constants.js
var require_constants = __commonJS((exports, module) => {
  var SEMVER_SPEC_VERSION = "2.0.0";
  var MAX_LENGTH = 256;
  var MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER || 9007199254740991;
  var MAX_SAFE_COMPONENT_LENGTH = 16;
  var MAX_SAFE_BUILD_LENGTH = MAX_LENGTH - 6;
  var RELEASE_TYPES = [
    "major",
    "premajor",
    "minor",
    "preminor",
    "patch",
    "prepatch",
    "prerelease"
  ];
  module.exports = {
    MAX_LENGTH,
    MAX_SAFE_COMPONENT_LENGTH,
    MAX_SAFE_BUILD_LENGTH,
    MAX_SAFE_INTEGER,
    RELEASE_TYPES,
    SEMVER_SPEC_VERSION,
    FLAG_INCLUDE_PRERELEASE: 1,
    FLAG_LOOSE: 2
  };
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/internal/debug.js
var require_debug2 = __commonJS((exports, module) => {
  var debug = typeof process === "object" && process.env && process.env.NODE_DEBUG && /\bsemver\b/i.test(process.env.NODE_DEBUG) ? (...args) => console.error("SEMVER", ...args) : () => {};
  module.exports = debug;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/internal/re.js
var require_re = __commonJS((exports, module) => {
  var {
    MAX_SAFE_COMPONENT_LENGTH,
    MAX_SAFE_BUILD_LENGTH,
    MAX_LENGTH
  } = require_constants();
  var debug = require_debug2();
  exports = module.exports = {};
  var re = exports.re = [];
  var safeRe = exports.safeRe = [];
  var src = exports.src = [];
  var safeSrc = exports.safeSrc = [];
  var t = exports.t = {};
  var R = 0;
  var LETTERDASHNUMBER = "[a-zA-Z0-9-]";
  var safeRegexReplacements = [
    ["\\s", 1],
    ["\\d", MAX_LENGTH],
    [LETTERDASHNUMBER, MAX_SAFE_BUILD_LENGTH]
  ];
  var makeSafeRegex = (value) => {
    for (const [token, max] of safeRegexReplacements) {
      value = value.split(`${token}*`).join(`${token}{0,${max}}`).split(`${token}+`).join(`${token}{1,${max}}`);
    }
    return value;
  };
  var createToken = (name, value, isGlobal) => {
    const safe = makeSafeRegex(value);
    const index = R++;
    debug(name, index, value);
    t[name] = index;
    src[index] = value;
    safeSrc[index] = safe;
    re[index] = new RegExp(value, isGlobal ? "g" : undefined);
    safeRe[index] = new RegExp(safe, isGlobal ? "g" : undefined);
  };
  createToken("NUMERICIDENTIFIER", "0|[1-9]\\d*");
  createToken("NUMERICIDENTIFIERLOOSE", "\\d+");
  createToken("NONNUMERICIDENTIFIER", `\\d*[a-zA-Z-]${LETTERDASHNUMBER}*`);
  createToken("MAINVERSION", `(${src[t.NUMERICIDENTIFIER]})\\.` + `(${src[t.NUMERICIDENTIFIER]})\\.` + `(${src[t.NUMERICIDENTIFIER]})`);
  createToken("MAINVERSIONLOOSE", `(${src[t.NUMERICIDENTIFIERLOOSE]})\\.` + `(${src[t.NUMERICIDENTIFIERLOOSE]})\\.` + `(${src[t.NUMERICIDENTIFIERLOOSE]})`);
  createToken("PRERELEASEIDENTIFIER", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIER]})`);
  createToken("PRERELEASEIDENTIFIERLOOSE", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIERLOOSE]})`);
  createToken("PRERELEASE", `(?:-(${src[t.PRERELEASEIDENTIFIER]}(?:\\.${src[t.PRERELEASEIDENTIFIER]})*))`);
  createToken("PRERELEASELOOSE", `(?:-?(${src[t.PRERELEASEIDENTIFIERLOOSE]}(?:\\.${src[t.PRERELEASEIDENTIFIERLOOSE]})*))`);
  createToken("BUILDIDENTIFIER", `${LETTERDASHNUMBER}+`);
  createToken("BUILD", `(?:\\+(${src[t.BUILDIDENTIFIER]}(?:\\.${src[t.BUILDIDENTIFIER]})*))`);
  createToken("FULLPLAIN", `v?${src[t.MAINVERSION]}${src[t.PRERELEASE]}?${src[t.BUILD]}?`);
  createToken("FULL", `^${src[t.FULLPLAIN]}$`);
  createToken("LOOSEPLAIN", `[v=\\s]*${src[t.MAINVERSIONLOOSE]}${src[t.PRERELEASELOOSE]}?${src[t.BUILD]}?`);
  createToken("LOOSE", `^${src[t.LOOSEPLAIN]}$`);
  createToken("GTLT", "((?:<|>)?=?)");
  createToken("XRANGEIDENTIFIERLOOSE", `${src[t.NUMERICIDENTIFIERLOOSE]}|x|X|\\*`);
  createToken("XRANGEIDENTIFIER", `${src[t.NUMERICIDENTIFIER]}|x|X|\\*`);
  createToken("XRANGEPLAIN", `[v=\\s]*(${src[t.XRANGEIDENTIFIER]})` + `(?:\\.(${src[t.XRANGEIDENTIFIER]})` + `(?:\\.(${src[t.XRANGEIDENTIFIER]})` + `(?:${src[t.PRERELEASE]})?${src[t.BUILD]}?` + `)?)?`);
  createToken("XRANGEPLAINLOOSE", `[v=\\s]*(${src[t.XRANGEIDENTIFIERLOOSE]})` + `(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})` + `(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})` + `(?:${src[t.PRERELEASELOOSE]})?${src[t.BUILD]}?` + `)?)?`);
  createToken("XRANGE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAIN]}$`);
  createToken("XRANGELOOSE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAINLOOSE]}$`);
  createToken("COERCEPLAIN", `${"(^|[^\\d])" + "(\\d{1,"}${MAX_SAFE_COMPONENT_LENGTH}})` + `(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?` + `(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?`);
  createToken("COERCE", `${src[t.COERCEPLAIN]}(?:$|[^\\d])`);
  createToken("COERCEFULL", src[t.COERCEPLAIN] + `(?:${src[t.PRERELEASE]})?` + `(?:${src[t.BUILD]})?` + `(?:$|[^\\d])`);
  createToken("COERCERTL", src[t.COERCE], true);
  createToken("COERCERTLFULL", src[t.COERCEFULL], true);
  createToken("LONETILDE", "(?:~>?)");
  createToken("TILDETRIM", `(\\s*)${src[t.LONETILDE]}\\s+`, true);
  exports.tildeTrimReplace = "$1~";
  createToken("TILDE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAIN]}$`);
  createToken("TILDELOOSE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAINLOOSE]}$`);
  createToken("LONECARET", "(?:\\^)");
  createToken("CARETTRIM", `(\\s*)${src[t.LONECARET]}\\s+`, true);
  exports.caretTrimReplace = "$1^";
  createToken("CARET", `^${src[t.LONECARET]}${src[t.XRANGEPLAIN]}$`);
  createToken("CARETLOOSE", `^${src[t.LONECARET]}${src[t.XRANGEPLAINLOOSE]}$`);
  createToken("COMPARATORLOOSE", `^${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]})$|^$`);
  createToken("COMPARATOR", `^${src[t.GTLT]}\\s*(${src[t.FULLPLAIN]})$|^$`);
  createToken("COMPARATORTRIM", `(\\s*)${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]}|${src[t.XRANGEPLAIN]})`, true);
  exports.comparatorTrimReplace = "$1$2$3";
  createToken("HYPHENRANGE", `^\\s*(${src[t.XRANGEPLAIN]})` + `\\s+-\\s+` + `(${src[t.XRANGEPLAIN]})` + `\\s*$`);
  createToken("HYPHENRANGELOOSE", `^\\s*(${src[t.XRANGEPLAINLOOSE]})` + `\\s+-\\s+` + `(${src[t.XRANGEPLAINLOOSE]})` + `\\s*$`);
  createToken("STAR", "(<|>)?=?\\s*\\*");
  createToken("GTE0", "^\\s*>=\\s*0\\.0\\.0\\s*$");
  createToken("GTE0PRE", "^\\s*>=\\s*0\\.0\\.0-0\\s*$");
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/internal/parse-options.js
var require_parse_options = __commonJS((exports, module) => {
  var looseOption = Object.freeze({ loose: true });
  var emptyOpts = Object.freeze({});
  var parseOptions = (options) => {
    if (!options) {
      return emptyOpts;
    }
    if (typeof options !== "object") {
      return looseOption;
    }
    return options;
  };
  module.exports = parseOptions;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/internal/identifiers.js
var require_identifiers = __commonJS((exports, module) => {
  var numeric = /^[0-9]+$/;
  var compareIdentifiers = (a, b) => {
    if (typeof a === "number" && typeof b === "number") {
      return a === b ? 0 : a < b ? -1 : 1;
    }
    const anum = numeric.test(a);
    const bnum = numeric.test(b);
    if (anum && bnum) {
      a = +a;
      b = +b;
    }
    return a === b ? 0 : anum && !bnum ? -1 : bnum && !anum ? 1 : a < b ? -1 : 1;
  };
  var rcompareIdentifiers = (a, b) => compareIdentifiers(b, a);
  module.exports = {
    compareIdentifiers,
    rcompareIdentifiers
  };
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/classes/semver.js
var require_semver = __commonJS((exports, module) => {
  var debug = require_debug2();
  var { MAX_LENGTH, MAX_SAFE_INTEGER } = require_constants();
  var { safeRe: re, t } = require_re();
  var parseOptions = require_parse_options();
  var { compareIdentifiers } = require_identifiers();

  class SemVer {
    constructor(version, options) {
      options = parseOptions(options);
      if (version instanceof SemVer) {
        if (version.loose === !!options.loose && version.includePrerelease === !!options.includePrerelease) {
          return version;
        } else {
          version = version.version;
        }
      } else if (typeof version !== "string") {
        throw new TypeError(`Invalid version. Must be a string. Got type "${typeof version}".`);
      }
      if (version.length > MAX_LENGTH) {
        throw new TypeError(`version is longer than ${MAX_LENGTH} characters`);
      }
      debug("SemVer", version, options);
      this.options = options;
      this.loose = !!options.loose;
      this.includePrerelease = !!options.includePrerelease;
      const m = version.trim().match(options.loose ? re[t.LOOSE] : re[t.FULL]);
      if (!m) {
        throw new TypeError(`Invalid Version: ${version}`);
      }
      this.raw = version;
      this.major = +m[1];
      this.minor = +m[2];
      this.patch = +m[3];
      if (this.major > MAX_SAFE_INTEGER || this.major < 0) {
        throw new TypeError("Invalid major version");
      }
      if (this.minor > MAX_SAFE_INTEGER || this.minor < 0) {
        throw new TypeError("Invalid minor version");
      }
      if (this.patch > MAX_SAFE_INTEGER || this.patch < 0) {
        throw new TypeError("Invalid patch version");
      }
      if (!m[4]) {
        this.prerelease = [];
      } else {
        this.prerelease = m[4].split(".").map((id) => {
          if (/^[0-9]+$/.test(id)) {
            const num = +id;
            if (num >= 0 && num < MAX_SAFE_INTEGER) {
              return num;
            }
          }
          return id;
        });
      }
      this.build = m[5] ? m[5].split(".") : [];
      this.format();
    }
    format() {
      this.version = `${this.major}.${this.minor}.${this.patch}`;
      if (this.prerelease.length) {
        this.version += `-${this.prerelease.join(".")}`;
      }
      return this.version;
    }
    toString() {
      return this.version;
    }
    compare(other) {
      debug("SemVer.compare", this.version, this.options, other);
      if (!(other instanceof SemVer)) {
        if (typeof other === "string" && other === this.version) {
          return 0;
        }
        other = new SemVer(other, this.options);
      }
      if (other.version === this.version) {
        return 0;
      }
      return this.compareMain(other) || this.comparePre(other);
    }
    compareMain(other) {
      if (!(other instanceof SemVer)) {
        other = new SemVer(other, this.options);
      }
      if (this.major < other.major) {
        return -1;
      }
      if (this.major > other.major) {
        return 1;
      }
      if (this.minor < other.minor) {
        return -1;
      }
      if (this.minor > other.minor) {
        return 1;
      }
      if (this.patch < other.patch) {
        return -1;
      }
      if (this.patch > other.patch) {
        return 1;
      }
      return 0;
    }
    comparePre(other) {
      if (!(other instanceof SemVer)) {
        other = new SemVer(other, this.options);
      }
      if (this.prerelease.length && !other.prerelease.length) {
        return -1;
      } else if (!this.prerelease.length && other.prerelease.length) {
        return 1;
      } else if (!this.prerelease.length && !other.prerelease.length) {
        return 0;
      }
      let i = 0;
      do {
        const a = this.prerelease[i];
        const b = other.prerelease[i];
        debug("prerelease compare", i, a, b);
        if (a === undefined && b === undefined) {
          return 0;
        } else if (b === undefined) {
          return 1;
        } else if (a === undefined) {
          return -1;
        } else if (a === b) {
          continue;
        } else {
          return compareIdentifiers(a, b);
        }
      } while (++i);
    }
    compareBuild(other) {
      if (!(other instanceof SemVer)) {
        other = new SemVer(other, this.options);
      }
      let i = 0;
      do {
        const a = this.build[i];
        const b = other.build[i];
        debug("build compare", i, a, b);
        if (a === undefined && b === undefined) {
          return 0;
        } else if (b === undefined) {
          return 1;
        } else if (a === undefined) {
          return -1;
        } else if (a === b) {
          continue;
        } else {
          return compareIdentifiers(a, b);
        }
      } while (++i);
    }
    inc(release, identifier, identifierBase) {
      if (release.startsWith("pre")) {
        if (!identifier && identifierBase === false) {
          throw new Error("invalid increment argument: identifier is empty");
        }
        if (identifier) {
          const match = `-${identifier}`.match(this.options.loose ? re[t.PRERELEASELOOSE] : re[t.PRERELEASE]);
          if (!match || match[1] !== identifier) {
            throw new Error(`invalid identifier: ${identifier}`);
          }
        }
      }
      switch (release) {
        case "premajor":
          this.prerelease.length = 0;
          this.patch = 0;
          this.minor = 0;
          this.major++;
          this.inc("pre", identifier, identifierBase);
          break;
        case "preminor":
          this.prerelease.length = 0;
          this.patch = 0;
          this.minor++;
          this.inc("pre", identifier, identifierBase);
          break;
        case "prepatch":
          this.prerelease.length = 0;
          this.inc("patch", identifier, identifierBase);
          this.inc("pre", identifier, identifierBase);
          break;
        case "prerelease":
          if (this.prerelease.length === 0) {
            this.inc("patch", identifier, identifierBase);
          }
          this.inc("pre", identifier, identifierBase);
          break;
        case "release":
          if (this.prerelease.length === 0) {
            throw new Error(`version ${this.raw} is not a prerelease`);
          }
          this.prerelease.length = 0;
          break;
        case "major":
          if (this.minor !== 0 || this.patch !== 0 || this.prerelease.length === 0) {
            this.major++;
          }
          this.minor = 0;
          this.patch = 0;
          this.prerelease = [];
          break;
        case "minor":
          if (this.patch !== 0 || this.prerelease.length === 0) {
            this.minor++;
          }
          this.patch = 0;
          this.prerelease = [];
          break;
        case "patch":
          if (this.prerelease.length === 0) {
            this.patch++;
          }
          this.prerelease = [];
          break;
        case "pre": {
          const base = Number(identifierBase) ? 1 : 0;
          if (this.prerelease.length === 0) {
            this.prerelease = [base];
          } else {
            let i = this.prerelease.length;
            while (--i >= 0) {
              if (typeof this.prerelease[i] === "number") {
                this.prerelease[i]++;
                i = -2;
              }
            }
            if (i === -1) {
              if (identifier === this.prerelease.join(".") && identifierBase === false) {
                throw new Error("invalid increment argument: identifier already exists");
              }
              this.prerelease.push(base);
            }
          }
          if (identifier) {
            let prerelease = [identifier, base];
            if (identifierBase === false) {
              prerelease = [identifier];
            }
            if (compareIdentifiers(this.prerelease[0], identifier) === 0) {
              if (isNaN(this.prerelease[1])) {
                this.prerelease = prerelease;
              }
            } else {
              this.prerelease = prerelease;
            }
          }
          break;
        }
        default:
          throw new Error(`invalid increment argument: ${release}`);
      }
      this.raw = this.format();
      if (this.build.length) {
        this.raw += `+${this.build.join(".")}`;
      }
      return this;
    }
  }
  module.exports = SemVer;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/parse.js
var require_parse = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var parse = (version, options, throwErrors = false) => {
    if (version instanceof SemVer) {
      return version;
    }
    try {
      return new SemVer(version, options);
    } catch (er) {
      if (!throwErrors) {
        return null;
      }
      throw er;
    }
  };
  module.exports = parse;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/valid.js
var require_valid = __commonJS((exports, module) => {
  var parse = require_parse();
  var valid = (version, options) => {
    const v = parse(version, options);
    return v ? v.version : null;
  };
  module.exports = valid;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/clean.js
var require_clean = __commonJS((exports, module) => {
  var parse = require_parse();
  var clean = (version, options) => {
    const s = parse(version.trim().replace(/^[=v]+/, ""), options);
    return s ? s.version : null;
  };
  module.exports = clean;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/inc.js
var require_inc = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var inc = (version, release, options, identifier, identifierBase) => {
    if (typeof options === "string") {
      identifierBase = identifier;
      identifier = options;
      options = undefined;
    }
    try {
      return new SemVer(version instanceof SemVer ? version.version : version, options).inc(release, identifier, identifierBase).version;
    } catch (er) {
      return null;
    }
  };
  module.exports = inc;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/diff.js
var require_diff = __commonJS((exports, module) => {
  var parse = require_parse();
  var diff = (version1, version2) => {
    const v1 = parse(version1, null, true);
    const v2 = parse(version2, null, true);
    const comparison = v1.compare(v2);
    if (comparison === 0) {
      return null;
    }
    const v1Higher = comparison > 0;
    const highVersion = v1Higher ? v1 : v2;
    const lowVersion = v1Higher ? v2 : v1;
    const highHasPre = !!highVersion.prerelease.length;
    const lowHasPre = !!lowVersion.prerelease.length;
    if (lowHasPre && !highHasPre) {
      if (!lowVersion.patch && !lowVersion.minor) {
        return "major";
      }
      if (lowVersion.compareMain(highVersion) === 0) {
        if (lowVersion.minor && !lowVersion.patch) {
          return "minor";
        }
        return "patch";
      }
    }
    const prefix = highHasPre ? "pre" : "";
    if (v1.major !== v2.major) {
      return prefix + "major";
    }
    if (v1.minor !== v2.minor) {
      return prefix + "minor";
    }
    if (v1.patch !== v2.patch) {
      return prefix + "patch";
    }
    return "prerelease";
  };
  module.exports = diff;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/major.js
var require_major = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var major = (a, loose) => new SemVer(a, loose).major;
  module.exports = major;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/minor.js
var require_minor = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var minor = (a, loose) => new SemVer(a, loose).minor;
  module.exports = minor;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/patch.js
var require_patch = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var patch = (a, loose) => new SemVer(a, loose).patch;
  module.exports = patch;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/prerelease.js
var require_prerelease = __commonJS((exports, module) => {
  var parse = require_parse();
  var prerelease = (version, options) => {
    const parsed = parse(version, options);
    return parsed && parsed.prerelease.length ? parsed.prerelease : null;
  };
  module.exports = prerelease;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/compare.js
var require_compare = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var compare = (a, b, loose) => new SemVer(a, loose).compare(new SemVer(b, loose));
  module.exports = compare;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/rcompare.js
var require_rcompare = __commonJS((exports, module) => {
  var compare = require_compare();
  var rcompare = (a, b, loose) => compare(b, a, loose);
  module.exports = rcompare;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/compare-loose.js
var require_compare_loose = __commonJS((exports, module) => {
  var compare = require_compare();
  var compareLoose = (a, b) => compare(a, b, true);
  module.exports = compareLoose;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/compare-build.js
var require_compare_build = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var compareBuild = (a, b, loose) => {
    const versionA = new SemVer(a, loose);
    const versionB = new SemVer(b, loose);
    return versionA.compare(versionB) || versionA.compareBuild(versionB);
  };
  module.exports = compareBuild;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/sort.js
var require_sort = __commonJS((exports, module) => {
  var compareBuild = require_compare_build();
  var sort = (list, loose) => list.sort((a, b) => compareBuild(a, b, loose));
  module.exports = sort;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/rsort.js
var require_rsort = __commonJS((exports, module) => {
  var compareBuild = require_compare_build();
  var rsort = (list, loose) => list.sort((a, b) => compareBuild(b, a, loose));
  module.exports = rsort;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/gt.js
var require_gt = __commonJS((exports, module) => {
  var compare = require_compare();
  var gt = (a, b, loose) => compare(a, b, loose) > 0;
  module.exports = gt;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/lt.js
var require_lt = __commonJS((exports, module) => {
  var compare = require_compare();
  var lt = (a, b, loose) => compare(a, b, loose) < 0;
  module.exports = lt;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/eq.js
var require_eq = __commonJS((exports, module) => {
  var compare = require_compare();
  var eq = (a, b, loose) => compare(a, b, loose) === 0;
  module.exports = eq;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/neq.js
var require_neq = __commonJS((exports, module) => {
  var compare = require_compare();
  var neq = (a, b, loose) => compare(a, b, loose) !== 0;
  module.exports = neq;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/gte.js
var require_gte = __commonJS((exports, module) => {
  var compare = require_compare();
  var gte = (a, b, loose) => compare(a, b, loose) >= 0;
  module.exports = gte;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/lte.js
var require_lte = __commonJS((exports, module) => {
  var compare = require_compare();
  var lte = (a, b, loose) => compare(a, b, loose) <= 0;
  module.exports = lte;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/cmp.js
var require_cmp = __commonJS((exports, module) => {
  var eq = require_eq();
  var neq = require_neq();
  var gt = require_gt();
  var gte = require_gte();
  var lt = require_lt();
  var lte = require_lte();
  var cmp = (a, op, b, loose) => {
    switch (op) {
      case "===":
        if (typeof a === "object") {
          a = a.version;
        }
        if (typeof b === "object") {
          b = b.version;
        }
        return a === b;
      case "!==":
        if (typeof a === "object") {
          a = a.version;
        }
        if (typeof b === "object") {
          b = b.version;
        }
        return a !== b;
      case "":
      case "=":
      case "==":
        return eq(a, b, loose);
      case "!=":
        return neq(a, b, loose);
      case ">":
        return gt(a, b, loose);
      case ">=":
        return gte(a, b, loose);
      case "<":
        return lt(a, b, loose);
      case "<=":
        return lte(a, b, loose);
      default:
        throw new TypeError(`Invalid operator: ${op}`);
    }
  };
  module.exports = cmp;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/coerce.js
var require_coerce = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var parse = require_parse();
  var { safeRe: re, t } = require_re();
  var coerce = (version, options) => {
    if (version instanceof SemVer) {
      return version;
    }
    if (typeof version === "number") {
      version = String(version);
    }
    if (typeof version !== "string") {
      return null;
    }
    options = options || {};
    let match = null;
    if (!options.rtl) {
      match = version.match(options.includePrerelease ? re[t.COERCEFULL] : re[t.COERCE]);
    } else {
      const coerceRtlRegex = options.includePrerelease ? re[t.COERCERTLFULL] : re[t.COERCERTL];
      let next;
      while ((next = coerceRtlRegex.exec(version)) && (!match || match.index + match[0].length !== version.length)) {
        if (!match || next.index + next[0].length !== match.index + match[0].length) {
          match = next;
        }
        coerceRtlRegex.lastIndex = next.index + next[1].length + next[2].length;
      }
      coerceRtlRegex.lastIndex = -1;
    }
    if (match === null) {
      return null;
    }
    const major = match[2];
    const minor = match[3] || "0";
    const patch = match[4] || "0";
    const prerelease = options.includePrerelease && match[5] ? `-${match[5]}` : "";
    const build = options.includePrerelease && match[6] ? `+${match[6]}` : "";
    return parse(`${major}.${minor}.${patch}${prerelease}${build}`, options);
  };
  module.exports = coerce;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/internal/lrucache.js
var require_lrucache = __commonJS((exports, module) => {
  class LRUCache {
    constructor() {
      this.max = 1000;
      this.map = new Map;
    }
    get(key) {
      const value = this.map.get(key);
      if (value === undefined) {
        return;
      } else {
        this.map.delete(key);
        this.map.set(key, value);
        return value;
      }
    }
    delete(key) {
      return this.map.delete(key);
    }
    set(key, value) {
      const deleted = this.delete(key);
      if (!deleted && value !== undefined) {
        if (this.map.size >= this.max) {
          const firstKey = this.map.keys().next().value;
          this.delete(firstKey);
        }
        this.map.set(key, value);
      }
      return this;
    }
  }
  module.exports = LRUCache;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/classes/range.js
var require_range = __commonJS((exports, module) => {
  var SPACE_CHARACTERS = /\s+/g;

  class Range {
    constructor(range, options) {
      options = parseOptions(options);
      if (range instanceof Range) {
        if (range.loose === !!options.loose && range.includePrerelease === !!options.includePrerelease) {
          return range;
        } else {
          return new Range(range.raw, options);
        }
      }
      if (range instanceof Comparator) {
        this.raw = range.value;
        this.set = [[range]];
        this.formatted = undefined;
        return this;
      }
      this.options = options;
      this.loose = !!options.loose;
      this.includePrerelease = !!options.includePrerelease;
      this.raw = range.trim().replace(SPACE_CHARACTERS, " ");
      this.set = this.raw.split("||").map((r) => this.parseRange(r.trim())).filter((c) => c.length);
      if (!this.set.length) {
        throw new TypeError(`Invalid SemVer Range: ${this.raw}`);
      }
      if (this.set.length > 1) {
        const first = this.set[0];
        this.set = this.set.filter((c) => !isNullSet(c[0]));
        if (this.set.length === 0) {
          this.set = [first];
        } else if (this.set.length > 1) {
          for (const c of this.set) {
            if (c.length === 1 && isAny(c[0])) {
              this.set = [c];
              break;
            }
          }
        }
      }
      this.formatted = undefined;
    }
    get range() {
      if (this.formatted === undefined) {
        this.formatted = "";
        for (let i = 0;i < this.set.length; i++) {
          if (i > 0) {
            this.formatted += "||";
          }
          const comps = this.set[i];
          for (let k = 0;k < comps.length; k++) {
            if (k > 0) {
              this.formatted += " ";
            }
            this.formatted += comps[k].toString().trim();
          }
        }
      }
      return this.formatted;
    }
    format() {
      return this.range;
    }
    toString() {
      return this.range;
    }
    parseRange(range) {
      const memoOpts = (this.options.includePrerelease && FLAG_INCLUDE_PRERELEASE) | (this.options.loose && FLAG_LOOSE);
      const memoKey = memoOpts + ":" + range;
      const cached = cache.get(memoKey);
      if (cached) {
        return cached;
      }
      const loose = this.options.loose;
      const hr = loose ? re[t.HYPHENRANGELOOSE] : re[t.HYPHENRANGE];
      range = range.replace(hr, hyphenReplace(this.options.includePrerelease));
      debug("hyphen replace", range);
      range = range.replace(re[t.COMPARATORTRIM], comparatorTrimReplace);
      debug("comparator trim", range);
      range = range.replace(re[t.TILDETRIM], tildeTrimReplace);
      debug("tilde trim", range);
      range = range.replace(re[t.CARETTRIM], caretTrimReplace);
      debug("caret trim", range);
      let rangeList = range.split(" ").map((comp) => parseComparator(comp, this.options)).join(" ").split(/\s+/).map((comp) => replaceGTE0(comp, this.options));
      if (loose) {
        rangeList = rangeList.filter((comp) => {
          debug("loose invalid filter", comp, this.options);
          return !!comp.match(re[t.COMPARATORLOOSE]);
        });
      }
      debug("range list", rangeList);
      const rangeMap = new Map;
      const comparators = rangeList.map((comp) => new Comparator(comp, this.options));
      for (const comp of comparators) {
        if (isNullSet(comp)) {
          return [comp];
        }
        rangeMap.set(comp.value, comp);
      }
      if (rangeMap.size > 1 && rangeMap.has("")) {
        rangeMap.delete("");
      }
      const result = [...rangeMap.values()];
      cache.set(memoKey, result);
      return result;
    }
    intersects(range, options) {
      if (!(range instanceof Range)) {
        throw new TypeError("a Range is required");
      }
      return this.set.some((thisComparators) => {
        return isSatisfiable(thisComparators, options) && range.set.some((rangeComparators) => {
          return isSatisfiable(rangeComparators, options) && thisComparators.every((thisComparator) => {
            return rangeComparators.every((rangeComparator) => {
              return thisComparator.intersects(rangeComparator, options);
            });
          });
        });
      });
    }
    test(version) {
      if (!version) {
        return false;
      }
      if (typeof version === "string") {
        try {
          version = new SemVer(version, this.options);
        } catch (er) {
          return false;
        }
      }
      for (let i = 0;i < this.set.length; i++) {
        if (testSet(this.set[i], version, this.options)) {
          return true;
        }
      }
      return false;
    }
  }
  module.exports = Range;
  var LRU = require_lrucache();
  var cache = new LRU;
  var parseOptions = require_parse_options();
  var Comparator = require_comparator();
  var debug = require_debug2();
  var SemVer = require_semver();
  var {
    safeRe: re,
    t,
    comparatorTrimReplace,
    tildeTrimReplace,
    caretTrimReplace
  } = require_re();
  var { FLAG_INCLUDE_PRERELEASE, FLAG_LOOSE } = require_constants();
  var isNullSet = (c) => c.value === "<0.0.0-0";
  var isAny = (c) => c.value === "";
  var isSatisfiable = (comparators, options) => {
    let result = true;
    const remainingComparators = comparators.slice();
    let testComparator = remainingComparators.pop();
    while (result && remainingComparators.length) {
      result = remainingComparators.every((otherComparator) => {
        return testComparator.intersects(otherComparator, options);
      });
      testComparator = remainingComparators.pop();
    }
    return result;
  };
  var parseComparator = (comp, options) => {
    comp = comp.replace(re[t.BUILD], "");
    debug("comp", comp, options);
    comp = replaceCarets(comp, options);
    debug("caret", comp);
    comp = replaceTildes(comp, options);
    debug("tildes", comp);
    comp = replaceXRanges(comp, options);
    debug("xrange", comp);
    comp = replaceStars(comp, options);
    debug("stars", comp);
    return comp;
  };
  var isX = (id) => !id || id.toLowerCase() === "x" || id === "*";
  var replaceTildes = (comp, options) => {
    return comp.trim().split(/\s+/).map((c) => replaceTilde(c, options)).join(" ");
  };
  var replaceTilde = (comp, options) => {
    const r = options.loose ? re[t.TILDELOOSE] : re[t.TILDE];
    return comp.replace(r, (_, M, m, p, pr) => {
      debug("tilde", comp, _, M, m, p, pr);
      let ret;
      if (isX(M)) {
        ret = "";
      } else if (isX(m)) {
        ret = `>=${M}.0.0 <${+M + 1}.0.0-0`;
      } else if (isX(p)) {
        ret = `>=${M}.${m}.0 <${M}.${+m + 1}.0-0`;
      } else if (pr) {
        debug("replaceTilde pr", pr);
        ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
      } else {
        ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`;
      }
      debug("tilde return", ret);
      return ret;
    });
  };
  var replaceCarets = (comp, options) => {
    return comp.trim().split(/\s+/).map((c) => replaceCaret(c, options)).join(" ");
  };
  var replaceCaret = (comp, options) => {
    debug("caret", comp, options);
    const r = options.loose ? re[t.CARETLOOSE] : re[t.CARET];
    const z = options.includePrerelease ? "-0" : "";
    return comp.replace(r, (_, M, m, p, pr) => {
      debug("caret", comp, _, M, m, p, pr);
      let ret;
      if (isX(M)) {
        ret = "";
      } else if (isX(m)) {
        ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`;
      } else if (isX(p)) {
        if (M === "0") {
          ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`;
        } else {
          ret = `>=${M}.${m}.0${z} <${+M + 1}.0.0-0`;
        }
      } else if (pr) {
        debug("replaceCaret pr", pr);
        if (M === "0") {
          if (m === "0") {
            ret = `>=${M}.${m}.${p}-${pr} <${M}.${m}.${+p + 1}-0`;
          } else {
            ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
          }
        } else {
          ret = `>=${M}.${m}.${p}-${pr} <${+M + 1}.0.0-0`;
        }
      } else {
        debug("no pr");
        if (M === "0") {
          if (m === "0") {
            ret = `>=${M}.${m}.${p}${z} <${M}.${m}.${+p + 1}-0`;
          } else {
            ret = `>=${M}.${m}.${p}${z} <${M}.${+m + 1}.0-0`;
          }
        } else {
          ret = `>=${M}.${m}.${p} <${+M + 1}.0.0-0`;
        }
      }
      debug("caret return", ret);
      return ret;
    });
  };
  var replaceXRanges = (comp, options) => {
    debug("replaceXRanges", comp, options);
    return comp.split(/\s+/).map((c) => replaceXRange(c, options)).join(" ");
  };
  var replaceXRange = (comp, options) => {
    comp = comp.trim();
    const r = options.loose ? re[t.XRANGELOOSE] : re[t.XRANGE];
    return comp.replace(r, (ret, gtlt, M, m, p, pr) => {
      debug("xRange", comp, ret, gtlt, M, m, p, pr);
      const xM = isX(M);
      const xm = xM || isX(m);
      const xp = xm || isX(p);
      const anyX = xp;
      if (gtlt === "=" && anyX) {
        gtlt = "";
      }
      pr = options.includePrerelease ? "-0" : "";
      if (xM) {
        if (gtlt === ">" || gtlt === "<") {
          ret = "<0.0.0-0";
        } else {
          ret = "*";
        }
      } else if (gtlt && anyX) {
        if (xm) {
          m = 0;
        }
        p = 0;
        if (gtlt === ">") {
          gtlt = ">=";
          if (xm) {
            M = +M + 1;
            m = 0;
            p = 0;
          } else {
            m = +m + 1;
            p = 0;
          }
        } else if (gtlt === "<=") {
          gtlt = "<";
          if (xm) {
            M = +M + 1;
          } else {
            m = +m + 1;
          }
        }
        if (gtlt === "<") {
          pr = "-0";
        }
        ret = `${gtlt + M}.${m}.${p}${pr}`;
      } else if (xm) {
        ret = `>=${M}.0.0${pr} <${+M + 1}.0.0-0`;
      } else if (xp) {
        ret = `>=${M}.${m}.0${pr} <${M}.${+m + 1}.0-0`;
      }
      debug("xRange return", ret);
      return ret;
    });
  };
  var replaceStars = (comp, options) => {
    debug("replaceStars", comp, options);
    return comp.trim().replace(re[t.STAR], "");
  };
  var replaceGTE0 = (comp, options) => {
    debug("replaceGTE0", comp, options);
    return comp.trim().replace(re[options.includePrerelease ? t.GTE0PRE : t.GTE0], "");
  };
  var hyphenReplace = (incPr) => ($0, from, fM, fm, fp, fpr, fb, to, tM, tm, tp, tpr) => {
    if (isX(fM)) {
      from = "";
    } else if (isX(fm)) {
      from = `>=${fM}.0.0${incPr ? "-0" : ""}`;
    } else if (isX(fp)) {
      from = `>=${fM}.${fm}.0${incPr ? "-0" : ""}`;
    } else if (fpr) {
      from = `>=${from}`;
    } else {
      from = `>=${from}${incPr ? "-0" : ""}`;
    }
    if (isX(tM)) {
      to = "";
    } else if (isX(tm)) {
      to = `<${+tM + 1}.0.0-0`;
    } else if (isX(tp)) {
      to = `<${tM}.${+tm + 1}.0-0`;
    } else if (tpr) {
      to = `<=${tM}.${tm}.${tp}-${tpr}`;
    } else if (incPr) {
      to = `<${tM}.${tm}.${+tp + 1}-0`;
    } else {
      to = `<=${to}`;
    }
    return `${from} ${to}`.trim();
  };
  var testSet = (set, version, options) => {
    for (let i = 0;i < set.length; i++) {
      if (!set[i].test(version)) {
        return false;
      }
    }
    if (version.prerelease.length && !options.includePrerelease) {
      for (let i = 0;i < set.length; i++) {
        debug(set[i].semver);
        if (set[i].semver === Comparator.ANY) {
          continue;
        }
        if (set[i].semver.prerelease.length > 0) {
          const allowed = set[i].semver;
          if (allowed.major === version.major && allowed.minor === version.minor && allowed.patch === version.patch) {
            return true;
          }
        }
      }
      return false;
    }
    return true;
  };
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/classes/comparator.js
var require_comparator = __commonJS((exports, module) => {
  var ANY = Symbol("SemVer ANY");

  class Comparator {
    static get ANY() {
      return ANY;
    }
    constructor(comp, options) {
      options = parseOptions(options);
      if (comp instanceof Comparator) {
        if (comp.loose === !!options.loose) {
          return comp;
        } else {
          comp = comp.value;
        }
      }
      comp = comp.trim().split(/\s+/).join(" ");
      debug("comparator", comp, options);
      this.options = options;
      this.loose = !!options.loose;
      this.parse(comp);
      if (this.semver === ANY) {
        this.value = "";
      } else {
        this.value = this.operator + this.semver.version;
      }
      debug("comp", this);
    }
    parse(comp) {
      const r = this.options.loose ? re[t.COMPARATORLOOSE] : re[t.COMPARATOR];
      const m = comp.match(r);
      if (!m) {
        throw new TypeError(`Invalid comparator: ${comp}`);
      }
      this.operator = m[1] !== undefined ? m[1] : "";
      if (this.operator === "=") {
        this.operator = "";
      }
      if (!m[2]) {
        this.semver = ANY;
      } else {
        this.semver = new SemVer(m[2], this.options.loose);
      }
    }
    toString() {
      return this.value;
    }
    test(version) {
      debug("Comparator.test", version, this.options.loose);
      if (this.semver === ANY || version === ANY) {
        return true;
      }
      if (typeof version === "string") {
        try {
          version = new SemVer(version, this.options);
        } catch (er) {
          return false;
        }
      }
      return cmp(version, this.operator, this.semver, this.options);
    }
    intersects(comp, options) {
      if (!(comp instanceof Comparator)) {
        throw new TypeError("a Comparator is required");
      }
      if (this.operator === "") {
        if (this.value === "") {
          return true;
        }
        return new Range(comp.value, options).test(this.value);
      } else if (comp.operator === "") {
        if (comp.value === "") {
          return true;
        }
        return new Range(this.value, options).test(comp.semver);
      }
      options = parseOptions(options);
      if (options.includePrerelease && (this.value === "<0.0.0-0" || comp.value === "<0.0.0-0")) {
        return false;
      }
      if (!options.includePrerelease && (this.value.startsWith("<0.0.0") || comp.value.startsWith("<0.0.0"))) {
        return false;
      }
      if (this.operator.startsWith(">") && comp.operator.startsWith(">")) {
        return true;
      }
      if (this.operator.startsWith("<") && comp.operator.startsWith("<")) {
        return true;
      }
      if (this.semver.version === comp.semver.version && this.operator.includes("=") && comp.operator.includes("=")) {
        return true;
      }
      if (cmp(this.semver, "<", comp.semver, options) && this.operator.startsWith(">") && comp.operator.startsWith("<")) {
        return true;
      }
      if (cmp(this.semver, ">", comp.semver, options) && this.operator.startsWith("<") && comp.operator.startsWith(">")) {
        return true;
      }
      return false;
    }
  }
  module.exports = Comparator;
  var parseOptions = require_parse_options();
  var { safeRe: re, t } = require_re();
  var cmp = require_cmp();
  var debug = require_debug2();
  var SemVer = require_semver();
  var Range = require_range();
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/functions/satisfies.js
var require_satisfies = __commonJS((exports, module) => {
  var Range = require_range();
  var satisfies = (version, range, options) => {
    try {
      range = new Range(range, options);
    } catch (er) {
      return false;
    }
    return range.test(version);
  };
  module.exports = satisfies;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/to-comparators.js
var require_to_comparators = __commonJS((exports, module) => {
  var Range = require_range();
  var toComparators = (range, options) => new Range(range, options).set.map((comp) => comp.map((c) => c.value).join(" ").trim().split(" "));
  module.exports = toComparators;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/max-satisfying.js
var require_max_satisfying = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var Range = require_range();
  var maxSatisfying = (versions, range, options) => {
    let max = null;
    let maxSV = null;
    let rangeObj = null;
    try {
      rangeObj = new Range(range, options);
    } catch (er) {
      return null;
    }
    versions.forEach((v) => {
      if (rangeObj.test(v)) {
        if (!max || maxSV.compare(v) === -1) {
          max = v;
          maxSV = new SemVer(max, options);
        }
      }
    });
    return max;
  };
  module.exports = maxSatisfying;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/min-satisfying.js
var require_min_satisfying = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var Range = require_range();
  var minSatisfying = (versions, range, options) => {
    let min = null;
    let minSV = null;
    let rangeObj = null;
    try {
      rangeObj = new Range(range, options);
    } catch (er) {
      return null;
    }
    versions.forEach((v) => {
      if (rangeObj.test(v)) {
        if (!min || minSV.compare(v) === 1) {
          min = v;
          minSV = new SemVer(min, options);
        }
      }
    });
    return min;
  };
  module.exports = minSatisfying;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/min-version.js
var require_min_version = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var Range = require_range();
  var gt = require_gt();
  var minVersion = (range, loose) => {
    range = new Range(range, loose);
    let minver = new SemVer("0.0.0");
    if (range.test(minver)) {
      return minver;
    }
    minver = new SemVer("0.0.0-0");
    if (range.test(minver)) {
      return minver;
    }
    minver = null;
    for (let i = 0;i < range.set.length; ++i) {
      const comparators = range.set[i];
      let setMin = null;
      comparators.forEach((comparator) => {
        const compver = new SemVer(comparator.semver.version);
        switch (comparator.operator) {
          case ">":
            if (compver.prerelease.length === 0) {
              compver.patch++;
            } else {
              compver.prerelease.push(0);
            }
            compver.raw = compver.format();
          case "":
          case ">=":
            if (!setMin || gt(compver, setMin)) {
              setMin = compver;
            }
            break;
          case "<":
          case "<=":
            break;
          default:
            throw new Error(`Unexpected operation: ${comparator.operator}`);
        }
      });
      if (setMin && (!minver || gt(minver, setMin))) {
        minver = setMin;
      }
    }
    if (minver && range.test(minver)) {
      return minver;
    }
    return null;
  };
  module.exports = minVersion;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/valid.js
var require_valid2 = __commonJS((exports, module) => {
  var Range = require_range();
  var validRange = (range, options) => {
    try {
      return new Range(range, options).range || "*";
    } catch (er) {
      return null;
    }
  };
  module.exports = validRange;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/outside.js
var require_outside = __commonJS((exports, module) => {
  var SemVer = require_semver();
  var Comparator = require_comparator();
  var { ANY } = Comparator;
  var Range = require_range();
  var satisfies = require_satisfies();
  var gt = require_gt();
  var lt = require_lt();
  var lte = require_lte();
  var gte = require_gte();
  var outside = (version, range, hilo, options) => {
    version = new SemVer(version, options);
    range = new Range(range, options);
    let gtfn, ltefn, ltfn, comp, ecomp;
    switch (hilo) {
      case ">":
        gtfn = gt;
        ltefn = lte;
        ltfn = lt;
        comp = ">";
        ecomp = ">=";
        break;
      case "<":
        gtfn = lt;
        ltefn = gte;
        ltfn = gt;
        comp = "<";
        ecomp = "<=";
        break;
      default:
        throw new TypeError('Must provide a hilo val of "<" or ">"');
    }
    if (satisfies(version, range, options)) {
      return false;
    }
    for (let i = 0;i < range.set.length; ++i) {
      const comparators = range.set[i];
      let high = null;
      let low = null;
      comparators.forEach((comparator) => {
        if (comparator.semver === ANY) {
          comparator = new Comparator(">=0.0.0");
        }
        high = high || comparator;
        low = low || comparator;
        if (gtfn(comparator.semver, high.semver, options)) {
          high = comparator;
        } else if (ltfn(comparator.semver, low.semver, options)) {
          low = comparator;
        }
      });
      if (high.operator === comp || high.operator === ecomp) {
        return false;
      }
      if ((!low.operator || low.operator === comp) && ltefn(version, low.semver)) {
        return false;
      } else if (low.operator === ecomp && ltfn(version, low.semver)) {
        return false;
      }
    }
    return true;
  };
  module.exports = outside;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/gtr.js
var require_gtr = __commonJS((exports, module) => {
  var outside = require_outside();
  var gtr = (version, range, options) => outside(version, range, ">", options);
  module.exports = gtr;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/ltr.js
var require_ltr = __commonJS((exports, module) => {
  var outside = require_outside();
  var ltr = (version, range, options) => outside(version, range, "<", options);
  module.exports = ltr;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/intersects.js
var require_intersects = __commonJS((exports, module) => {
  var Range = require_range();
  var intersects = (r1, r2, options) => {
    r1 = new Range(r1, options);
    r2 = new Range(r2, options);
    return r1.intersects(r2, options);
  };
  module.exports = intersects;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/simplify.js
var require_simplify = __commonJS((exports, module) => {
  var satisfies = require_satisfies();
  var compare = require_compare();
  module.exports = (versions, range, options) => {
    const set = [];
    let first = null;
    let prev = null;
    const v = versions.sort((a, b) => compare(a, b, options));
    for (const version of v) {
      const included = satisfies(version, range, options);
      if (included) {
        prev = version;
        if (!first) {
          first = version;
        }
      } else {
        if (prev) {
          set.push([first, prev]);
        }
        prev = null;
        first = null;
      }
    }
    if (first) {
      set.push([first, null]);
    }
    const ranges = [];
    for (const [min, max] of set) {
      if (min === max) {
        ranges.push(min);
      } else if (!max && min === v[0]) {
        ranges.push("*");
      } else if (!max) {
        ranges.push(`>=${min}`);
      } else if (min === v[0]) {
        ranges.push(`<=${max}`);
      } else {
        ranges.push(`${min} - ${max}`);
      }
    }
    const simplified = ranges.join(" || ");
    const original = typeof range.raw === "string" ? range.raw : String(range);
    return simplified.length < original.length ? simplified : range;
  };
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/ranges/subset.js
var require_subset = __commonJS((exports, module) => {
  var Range = require_range();
  var Comparator = require_comparator();
  var { ANY } = Comparator;
  var satisfies = require_satisfies();
  var compare = require_compare();
  var subset = (sub, dom, options = {}) => {
    if (sub === dom) {
      return true;
    }
    sub = new Range(sub, options);
    dom = new Range(dom, options);
    let sawNonNull = false;
    OUTER:
      for (const simpleSub of sub.set) {
        for (const simpleDom of dom.set) {
          const isSub = simpleSubset(simpleSub, simpleDom, options);
          sawNonNull = sawNonNull || isSub !== null;
          if (isSub) {
            continue OUTER;
          }
        }
        if (sawNonNull) {
          return false;
        }
      }
    return true;
  };
  var minimumVersionWithPreRelease = [new Comparator(">=0.0.0-0")];
  var minimumVersion = [new Comparator(">=0.0.0")];
  var simpleSubset = (sub, dom, options) => {
    if (sub === dom) {
      return true;
    }
    if (sub.length === 1 && sub[0].semver === ANY) {
      if (dom.length === 1 && dom[0].semver === ANY) {
        return true;
      } else if (options.includePrerelease) {
        sub = minimumVersionWithPreRelease;
      } else {
        sub = minimumVersion;
      }
    }
    if (dom.length === 1 && dom[0].semver === ANY) {
      if (options.includePrerelease) {
        return true;
      } else {
        dom = minimumVersion;
      }
    }
    const eqSet = new Set;
    let gt, lt;
    for (const c of sub) {
      if (c.operator === ">" || c.operator === ">=") {
        gt = higherGT(gt, c, options);
      } else if (c.operator === "<" || c.operator === "<=") {
        lt = lowerLT(lt, c, options);
      } else {
        eqSet.add(c.semver);
      }
    }
    if (eqSet.size > 1) {
      return null;
    }
    let gtltComp;
    if (gt && lt) {
      gtltComp = compare(gt.semver, lt.semver, options);
      if (gtltComp > 0) {
        return null;
      } else if (gtltComp === 0 && (gt.operator !== ">=" || lt.operator !== "<=")) {
        return null;
      }
    }
    for (const eq of eqSet) {
      if (gt && !satisfies(eq, String(gt), options)) {
        return null;
      }
      if (lt && !satisfies(eq, String(lt), options)) {
        return null;
      }
      for (const c of dom) {
        if (!satisfies(eq, String(c), options)) {
          return false;
        }
      }
      return true;
    }
    let higher, lower;
    let hasDomLT, hasDomGT;
    let needDomLTPre = lt && !options.includePrerelease && lt.semver.prerelease.length ? lt.semver : false;
    let needDomGTPre = gt && !options.includePrerelease && gt.semver.prerelease.length ? gt.semver : false;
    if (needDomLTPre && needDomLTPre.prerelease.length === 1 && lt.operator === "<" && needDomLTPre.prerelease[0] === 0) {
      needDomLTPre = false;
    }
    for (const c of dom) {
      hasDomGT = hasDomGT || c.operator === ">" || c.operator === ">=";
      hasDomLT = hasDomLT || c.operator === "<" || c.operator === "<=";
      if (gt) {
        if (needDomGTPre) {
          if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomGTPre.major && c.semver.minor === needDomGTPre.minor && c.semver.patch === needDomGTPre.patch) {
            needDomGTPre = false;
          }
        }
        if (c.operator === ">" || c.operator === ">=") {
          higher = higherGT(gt, c, options);
          if (higher === c && higher !== gt) {
            return false;
          }
        } else if (gt.operator === ">=" && !satisfies(gt.semver, String(c), options)) {
          return false;
        }
      }
      if (lt) {
        if (needDomLTPre) {
          if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomLTPre.major && c.semver.minor === needDomLTPre.minor && c.semver.patch === needDomLTPre.patch) {
            needDomLTPre = false;
          }
        }
        if (c.operator === "<" || c.operator === "<=") {
          lower = lowerLT(lt, c, options);
          if (lower === c && lower !== lt) {
            return false;
          }
        } else if (lt.operator === "<=" && !satisfies(lt.semver, String(c), options)) {
          return false;
        }
      }
      if (!c.operator && (lt || gt) && gtltComp !== 0) {
        return false;
      }
    }
    if (gt && hasDomLT && !lt && gtltComp !== 0) {
      return false;
    }
    if (lt && hasDomGT && !gt && gtltComp !== 0) {
      return false;
    }
    if (needDomGTPre || needDomLTPre) {
      return false;
    }
    return true;
  };
  var higherGT = (a, b, options) => {
    if (!a) {
      return b;
    }
    const comp = compare(a.semver, b.semver, options);
    return comp > 0 ? a : comp < 0 ? b : b.operator === ">" && a.operator === ">=" ? b : a;
  };
  var lowerLT = (a, b, options) => {
    if (!a) {
      return b;
    }
    const comp = compare(a.semver, b.semver, options);
    return comp < 0 ? a : comp > 0 ? b : b.operator === "<" && a.operator === "<=" ? b : a;
  };
  module.exports = subset;
});

// node_modules/@mapbox/node-pre-gyp/node_modules/semver/index.js
var require_semver2 = __commonJS((exports, module) => {
  var internalRe = require_re();
  var constants = require_constants();
  var SemVer = require_semver();
  var identifiers = require_identifiers();
  var parse = require_parse();
  var valid = require_valid();
  var clean = require_clean();
  var inc = require_inc();
  var diff = require_diff();
  var major = require_major();
  var minor = require_minor();
  var patch = require_patch();
  var prerelease = require_prerelease();
  var compare = require_compare();
  var rcompare = require_rcompare();
  var compareLoose = require_compare_loose();
  var compareBuild = require_compare_build();
  var sort = require_sort();
  var rsort = require_rsort();
  var gt = require_gt();
  var lt = require_lt();
  var eq = require_eq();
  var neq = require_neq();
  var gte = require_gte();
  var lte = require_lte();
  var cmp = require_cmp();
  var coerce = require_coerce();
  var Comparator = require_comparator();
  var Range = require_range();
  var satisfies = require_satisfies();
  var toComparators = require_to_comparators();
  var maxSatisfying = require_max_satisfying();
  var minSatisfying = require_min_satisfying();
  var minVersion = require_min_version();
  var validRange = require_valid2();
  var outside = require_outside();
  var gtr = require_gtr();
  var ltr = require_ltr();
  var intersects = require_intersects();
  var simplifyRange = require_simplify();
  var subset = require_subset();
  module.exports = {
    parse,
    valid,
    clean,
    inc,
    diff,
    major,
    minor,
    patch,
    prerelease,
    compare,
    rcompare,
    compareLoose,
    compareBuild,
    sort,
    rsort,
    gt,
    lt,
    eq,
    neq,
    gte,
    lte,
    cmp,
    coerce,
    Comparator,
    Range,
    satisfies,
    toComparators,
    maxSatisfying,
    minSatisfying,
    minVersion,
    validRange,
    outside,
    gtr,
    ltr,
    intersects,
    simplifyRange,
    subset,
    SemVer,
    re: internalRe.re,
    src: internalRe.src,
    tokens: internalRe.t,
    SEMVER_SPEC_VERSION: constants.SEMVER_SPEC_VERSION,
    RELEASE_TYPES: constants.RELEASE_TYPES,
    compareIdentifiers: identifiers.compareIdentifiers,
    rcompareIdentifiers: identifiers.rcompareIdentifiers
  };
});

// node_modules/detect-libc/lib/process.js
var require_process = __commonJS((exports, module) => {
  var isLinux = () => process.platform === "linux";
  var report = null;
  var getReport = () => {
    if (!report) {
      if (isLinux() && process.report) {
        const orig = process.report.excludeNetwork;
        process.report.excludeNetwork = true;
        report = process.report.getReport();
        process.report.excludeNetwork = orig;
      } else {
        report = {};
      }
    }
    return report;
  };
  module.exports = { isLinux, getReport };
});

// node_modules/detect-libc/lib/filesystem.js
var require_filesystem = __commonJS((exports, module) => {
  var fs = __require("fs");
  var LDD_PATH = "/usr/bin/ldd";
  var SELF_PATH = "/proc/self/exe";
  var MAX_LENGTH = 2048;
  var readFileSync2 = (path) => {
    const fd = fs.openSync(path, "r");
    const buffer = Buffer.alloc(MAX_LENGTH);
    const bytesRead = fs.readSync(fd, buffer, 0, MAX_LENGTH, 0);
    fs.close(fd, () => {});
    return buffer.subarray(0, bytesRead);
  };
  var readFile = (path) => new Promise((resolve3, reject) => {
    fs.open(path, "r", (err, fd) => {
      if (err) {
        reject(err);
      } else {
        const buffer = Buffer.alloc(MAX_LENGTH);
        fs.read(fd, buffer, 0, MAX_LENGTH, 0, (_, bytesRead) => {
          resolve3(buffer.subarray(0, bytesRead));
          fs.close(fd, () => {});
        });
      }
    });
  });
  module.exports = {
    LDD_PATH,
    SELF_PATH,
    readFileSync: readFileSync2,
    readFile
  };
});

// node_modules/detect-libc/lib/elf.js
var require_elf = __commonJS((exports, module) => {
  var interpreterPath = (elf) => {
    if (elf.length < 64) {
      return null;
    }
    if (elf.readUInt32BE(0) !== 2135247942) {
      return null;
    }
    if (elf.readUInt8(4) !== 2) {
      return null;
    }
    if (elf.readUInt8(5) !== 1) {
      return null;
    }
    const offset = elf.readUInt32LE(32);
    const size = elf.readUInt16LE(54);
    const count = elf.readUInt16LE(56);
    for (let i = 0;i < count; i++) {
      const headerOffset = offset + i * size;
      const type = elf.readUInt32LE(headerOffset);
      if (type === 3) {
        const fileOffset = elf.readUInt32LE(headerOffset + 8);
        const fileSize = elf.readUInt32LE(headerOffset + 32);
        return elf.subarray(fileOffset, fileOffset + fileSize).toString().replace(/\0.*$/g, "");
      }
    }
    return null;
  };
  module.exports = {
    interpreterPath
  };
});

// node_modules/detect-libc/lib/detect-libc.js
var require_detect_libc = __commonJS((exports, module) => {
  var childProcess = __require("child_process");
  var { isLinux, getReport } = require_process();
  var { LDD_PATH, SELF_PATH, readFile, readFileSync: readFileSync2 } = require_filesystem();
  var { interpreterPath } = require_elf();
  var cachedFamilyInterpreter;
  var cachedFamilyFilesystem;
  var cachedVersionFilesystem;
  var command = "getconf GNU_LIBC_VERSION 2>&1 || true; ldd --version 2>&1 || true";
  var commandOut = "";
  var safeCommand = () => {
    if (!commandOut) {
      return new Promise((resolve3) => {
        childProcess.exec(command, (err, out) => {
          commandOut = err ? " " : out;
          resolve3(commandOut);
        });
      });
    }
    return commandOut;
  };
  var safeCommandSync = () => {
    if (!commandOut) {
      try {
        commandOut = childProcess.execSync(command, { encoding: "utf8" });
      } catch (_err) {
        commandOut = " ";
      }
    }
    return commandOut;
  };
  var GLIBC = "glibc";
  var RE_GLIBC_VERSION = /LIBC[a-z0-9 \-).]*?(\d+\.\d+)/i;
  var MUSL = "musl";
  var isFileMusl = (f) => f.includes("libc.musl-") || f.includes("ld-musl-");
  var familyFromReport = () => {
    const report = getReport();
    if (report.header && report.header.glibcVersionRuntime) {
      return GLIBC;
    }
    if (Array.isArray(report.sharedObjects)) {
      if (report.sharedObjects.some(isFileMusl)) {
        return MUSL;
      }
    }
    return null;
  };
  var familyFromCommand = (out) => {
    const [getconf, ldd1] = out.split(/[\r\n]+/);
    if (getconf && getconf.includes(GLIBC)) {
      return GLIBC;
    }
    if (ldd1 && ldd1.includes(MUSL)) {
      return MUSL;
    }
    return null;
  };
  var familyFromInterpreterPath = (path) => {
    if (path) {
      if (path.includes("/ld-musl-")) {
        return MUSL;
      } else if (path.includes("/ld-linux-")) {
        return GLIBC;
      }
    }
    return null;
  };
  var getFamilyFromLddContent = (content) => {
    content = content.toString();
    if (content.includes("musl")) {
      return MUSL;
    }
    if (content.includes("GNU C Library")) {
      return GLIBC;
    }
    return null;
  };
  var familyFromFilesystem = async () => {
    if (cachedFamilyFilesystem !== undefined) {
      return cachedFamilyFilesystem;
    }
    cachedFamilyFilesystem = null;
    try {
      const lddContent = await readFile(LDD_PATH);
      cachedFamilyFilesystem = getFamilyFromLddContent(lddContent);
    } catch (e) {}
    return cachedFamilyFilesystem;
  };
  var familyFromFilesystemSync = () => {
    if (cachedFamilyFilesystem !== undefined) {
      return cachedFamilyFilesystem;
    }
    cachedFamilyFilesystem = null;
    try {
      const lddContent = readFileSync2(LDD_PATH);
      cachedFamilyFilesystem = getFamilyFromLddContent(lddContent);
    } catch (e) {}
    return cachedFamilyFilesystem;
  };
  var familyFromInterpreter = async () => {
    if (cachedFamilyInterpreter !== undefined) {
      return cachedFamilyInterpreter;
    }
    cachedFamilyInterpreter = null;
    try {
      const selfContent = await readFile(SELF_PATH);
      const path = interpreterPath(selfContent);
      cachedFamilyInterpreter = familyFromInterpreterPath(path);
    } catch (e) {}
    return cachedFamilyInterpreter;
  };
  var familyFromInterpreterSync = () => {
    if (cachedFamilyInterpreter !== undefined) {
      return cachedFamilyInterpreter;
    }
    cachedFamilyInterpreter = null;
    try {
      const selfContent = readFileSync2(SELF_PATH);
      const path = interpreterPath(selfContent);
      cachedFamilyInterpreter = familyFromInterpreterPath(path);
    } catch (e) {}
    return cachedFamilyInterpreter;
  };
  var family = async () => {
    let family2 = null;
    if (isLinux()) {
      family2 = await familyFromInterpreter();
      if (!family2) {
        family2 = await familyFromFilesystem();
        if (!family2) {
          family2 = familyFromReport();
        }
        if (!family2) {
          const out = await safeCommand();
          family2 = familyFromCommand(out);
        }
      }
    }
    return family2;
  };
  var familySync = () => {
    let family2 = null;
    if (isLinux()) {
      family2 = familyFromInterpreterSync();
      if (!family2) {
        family2 = familyFromFilesystemSync();
        if (!family2) {
          family2 = familyFromReport();
        }
        if (!family2) {
          const out = safeCommandSync();
          family2 = familyFromCommand(out);
        }
      }
    }
    return family2;
  };
  var isNonGlibcLinux = async () => isLinux() && await family() !== GLIBC;
  var isNonGlibcLinuxSync = () => isLinux() && familySync() !== GLIBC;
  var versionFromFilesystem = async () => {
    if (cachedVersionFilesystem !== undefined) {
      return cachedVersionFilesystem;
    }
    cachedVersionFilesystem = null;
    try {
      const lddContent = await readFile(LDD_PATH);
      const versionMatch = lddContent.match(RE_GLIBC_VERSION);
      if (versionMatch) {
        cachedVersionFilesystem = versionMatch[1];
      }
    } catch (e) {}
    return cachedVersionFilesystem;
  };
  var versionFromFilesystemSync = () => {
    if (cachedVersionFilesystem !== undefined) {
      return cachedVersionFilesystem;
    }
    cachedVersionFilesystem = null;
    try {
      const lddContent = readFileSync2(LDD_PATH);
      const versionMatch = lddContent.match(RE_GLIBC_VERSION);
      if (versionMatch) {
        cachedVersionFilesystem = versionMatch[1];
      }
    } catch (e) {}
    return cachedVersionFilesystem;
  };
  var versionFromReport = () => {
    const report = getReport();
    if (report.header && report.header.glibcVersionRuntime) {
      return report.header.glibcVersionRuntime;
    }
    return null;
  };
  var versionSuffix = (s) => s.trim().split(/\s+/)[1];
  var versionFromCommand = (out) => {
    const [getconf, ldd1, ldd2] = out.split(/[\r\n]+/);
    if (getconf && getconf.includes(GLIBC)) {
      return versionSuffix(getconf);
    }
    if (ldd1 && ldd2 && ldd1.includes(MUSL)) {
      return versionSuffix(ldd2);
    }
    return null;
  };
  var version = async () => {
    let version2 = null;
    if (isLinux()) {
      version2 = await versionFromFilesystem();
      if (!version2) {
        version2 = versionFromReport();
      }
      if (!version2) {
        const out = await safeCommand();
        version2 = versionFromCommand(out);
      }
    }
    return version2;
  };
  var versionSync = () => {
    let version2 = null;
    if (isLinux()) {
      version2 = versionFromFilesystemSync();
      if (!version2) {
        version2 = versionFromReport();
      }
      if (!version2) {
        const out = safeCommandSync();
        version2 = versionFromCommand(out);
      }
    }
    return version2;
  };
  module.exports = {
    GLIBC,
    MUSL,
    family,
    familySync,
    isNonGlibcLinux,
    isNonGlibcLinuxSync,
    version,
    versionSync
  };
});

// node_modules/@mapbox/node-pre-gyp/lib/util/abi_crosswalk.json
var require_abi_crosswalk = __commonJS((exports, module) => {
  module.exports = {
    "0.1.14": {
      node_abi: null,
      v8: "1.3"
    },
    "0.1.15": {
      node_abi: null,
      v8: "1.3"
    },
    "0.1.16": {
      node_abi: null,
      v8: "1.3"
    },
    "0.1.17": {
      node_abi: null,
      v8: "1.3"
    },
    "0.1.18": {
      node_abi: null,
      v8: "1.3"
    },
    "0.1.19": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.20": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.21": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.22": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.23": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.24": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.25": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.26": {
      node_abi: null,
      v8: "2.0"
    },
    "0.1.27": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.28": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.29": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.30": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.31": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.32": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.33": {
      node_abi: null,
      v8: "2.1"
    },
    "0.1.90": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.91": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.92": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.93": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.94": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.95": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.96": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.97": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.98": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.99": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.100": {
      node_abi: null,
      v8: "2.2"
    },
    "0.1.101": {
      node_abi: null,
      v8: "2.3"
    },
    "0.1.102": {
      node_abi: null,
      v8: "2.3"
    },
    "0.1.103": {
      node_abi: null,
      v8: "2.3"
    },
    "0.1.104": {
      node_abi: null,
      v8: "2.3"
    },
    "0.2.0": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.2.1": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.2.2": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.2.3": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.2.4": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.2.5": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.2.6": {
      node_abi: 1,
      v8: "2.3"
    },
    "0.3.0": {
      node_abi: 1,
      v8: "2.5"
    },
    "0.3.1": {
      node_abi: 1,
      v8: "2.5"
    },
    "0.3.2": {
      node_abi: 1,
      v8: "3.0"
    },
    "0.3.3": {
      node_abi: 1,
      v8: "3.0"
    },
    "0.3.4": {
      node_abi: 1,
      v8: "3.0"
    },
    "0.3.5": {
      node_abi: 1,
      v8: "3.0"
    },
    "0.3.6": {
      node_abi: 1,
      v8: "3.0"
    },
    "0.3.7": {
      node_abi: 1,
      v8: "3.0"
    },
    "0.3.8": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.0": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.1": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.2": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.3": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.4": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.5": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.6": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.7": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.8": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.9": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.10": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.11": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.4.12": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.5.0": {
      node_abi: 1,
      v8: "3.1"
    },
    "0.5.1": {
      node_abi: 1,
      v8: "3.4"
    },
    "0.5.2": {
      node_abi: 1,
      v8: "3.4"
    },
    "0.5.3": {
      node_abi: 1,
      v8: "3.4"
    },
    "0.5.4": {
      node_abi: 1,
      v8: "3.5"
    },
    "0.5.5": {
      node_abi: 1,
      v8: "3.5"
    },
    "0.5.6": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.5.7": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.5.8": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.5.9": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.5.10": {
      node_abi: 1,
      v8: "3.7"
    },
    "0.6.0": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.1": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.2": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.3": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.4": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.5": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.6": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.7": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.8": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.9": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.10": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.11": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.12": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.13": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.14": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.15": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.16": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.17": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.18": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.19": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.20": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.6.21": {
      node_abi: 1,
      v8: "3.6"
    },
    "0.7.0": {
      node_abi: 1,
      v8: "3.8"
    },
    "0.7.1": {
      node_abi: 1,
      v8: "3.8"
    },
    "0.7.2": {
      node_abi: 1,
      v8: "3.8"
    },
    "0.7.3": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.4": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.5": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.6": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.7": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.8": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.9": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.7.10": {
      node_abi: 1,
      v8: "3.9"
    },
    "0.7.11": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.7.12": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.0": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.1": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.2": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.3": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.4": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.5": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.6": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.7": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.8": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.9": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.10": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.11": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.12": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.13": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.14": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.15": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.16": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.17": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.18": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.19": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.20": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.21": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.22": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.23": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.24": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.25": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.26": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.27": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.8.28": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.9.0": {
      node_abi: 1,
      v8: "3.11"
    },
    "0.9.1": {
      node_abi: 10,
      v8: "3.11"
    },
    "0.9.2": {
      node_abi: 10,
      v8: "3.11"
    },
    "0.9.3": {
      node_abi: 10,
      v8: "3.13"
    },
    "0.9.4": {
      node_abi: 10,
      v8: "3.13"
    },
    "0.9.5": {
      node_abi: 10,
      v8: "3.13"
    },
    "0.9.6": {
      node_abi: 10,
      v8: "3.15"
    },
    "0.9.7": {
      node_abi: 10,
      v8: "3.15"
    },
    "0.9.8": {
      node_abi: 10,
      v8: "3.15"
    },
    "0.9.9": {
      node_abi: 11,
      v8: "3.15"
    },
    "0.9.10": {
      node_abi: 11,
      v8: "3.15"
    },
    "0.9.11": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.9.12": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.0": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.1": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.2": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.3": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.4": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.5": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.6": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.7": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.8": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.9": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.10": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.11": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.12": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.13": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.14": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.15": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.16": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.17": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.18": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.19": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.20": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.21": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.22": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.23": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.24": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.25": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.26": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.27": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.28": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.29": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.30": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.31": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.32": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.33": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.34": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.35": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.36": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.37": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.38": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.39": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.40": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.41": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.42": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.43": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.44": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.45": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.46": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.47": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.10.48": {
      node_abi: 11,
      v8: "3.14"
    },
    "0.11.0": {
      node_abi: 12,
      v8: "3.17"
    },
    "0.11.1": {
      node_abi: 12,
      v8: "3.18"
    },
    "0.11.2": {
      node_abi: 12,
      v8: "3.19"
    },
    "0.11.3": {
      node_abi: 12,
      v8: "3.19"
    },
    "0.11.4": {
      node_abi: 12,
      v8: "3.20"
    },
    "0.11.5": {
      node_abi: 12,
      v8: "3.20"
    },
    "0.11.6": {
      node_abi: 12,
      v8: "3.20"
    },
    "0.11.7": {
      node_abi: 12,
      v8: "3.20"
    },
    "0.11.8": {
      node_abi: 13,
      v8: "3.21"
    },
    "0.11.9": {
      node_abi: 13,
      v8: "3.22"
    },
    "0.11.10": {
      node_abi: 13,
      v8: "3.22"
    },
    "0.11.11": {
      node_abi: 14,
      v8: "3.22"
    },
    "0.11.12": {
      node_abi: 14,
      v8: "3.22"
    },
    "0.11.13": {
      node_abi: 14,
      v8: "3.25"
    },
    "0.11.14": {
      node_abi: 14,
      v8: "3.26"
    },
    "0.11.15": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.11.16": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.0": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.1": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.2": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.3": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.4": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.5": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.6": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.7": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.8": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.9": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.10": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.11": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.12": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.13": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.14": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.15": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.16": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.17": {
      node_abi: 14,
      v8: "3.28"
    },
    "0.12.18": {
      node_abi: 14,
      v8: "3.28"
    },
    "1.0.0": {
      node_abi: 42,
      v8: "3.31"
    },
    "1.0.1": {
      node_abi: 42,
      v8: "3.31"
    },
    "1.0.2": {
      node_abi: 42,
      v8: "3.31"
    },
    "1.0.3": {
      node_abi: 42,
      v8: "4.1"
    },
    "1.0.4": {
      node_abi: 42,
      v8: "4.1"
    },
    "1.1.0": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.2.0": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.3.0": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.4.1": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.4.2": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.4.3": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.5.0": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.5.1": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.6.0": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.6.1": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.6.2": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.6.3": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.6.4": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.7.1": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.8.1": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.8.2": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.8.3": {
      node_abi: 43,
      v8: "4.1"
    },
    "1.8.4": {
      node_abi: 43,
      v8: "4.1"
    },
    "2.0.0": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.0.1": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.0.2": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.1.0": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.2.0": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.2.1": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.3.0": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.3.1": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.3.2": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.3.3": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.3.4": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.4.0": {
      node_abi: 44,
      v8: "4.2"
    },
    "2.5.0": {
      node_abi: 44,
      v8: "4.2"
    },
    "3.0.0": {
      node_abi: 45,
      v8: "4.4"
    },
    "3.1.0": {
      node_abi: 45,
      v8: "4.4"
    },
    "3.2.0": {
      node_abi: 45,
      v8: "4.4"
    },
    "3.3.0": {
      node_abi: 45,
      v8: "4.4"
    },
    "3.3.1": {
      node_abi: 45,
      v8: "4.4"
    },
    "4.0.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.1.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.1.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.1.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.3": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.4": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.5": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.2.6": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.3.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.3.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.3.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.3": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.4": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.5": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.6": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.4.7": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.5.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.6.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.6.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.6.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.7.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.7.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.7.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.7.3": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.2": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.3": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.4": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.5": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.6": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.8.7": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.9.0": {
      node_abi: 46,
      v8: "4.5"
    },
    "4.9.1": {
      node_abi: 46,
      v8: "4.5"
    },
    "5.0.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.1.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.1.1": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.2.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.3.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.4.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.4.1": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.5.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.6.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.7.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.7.1": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.8.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.9.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.9.1": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.10.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.10.1": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.11.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.11.1": {
      node_abi: 47,
      v8: "4.6"
    },
    "5.12.0": {
      node_abi: 47,
      v8: "4.6"
    },
    "6.0.0": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.1.0": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.2.0": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.2.1": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.2.2": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.3.0": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.3.1": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.4.0": {
      node_abi: 48,
      v8: "5.0"
    },
    "6.5.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.6.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.7.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.8.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.8.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.9.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.9.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.9.2": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.9.3": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.9.4": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.9.5": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.10.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.10.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.10.2": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.10.3": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.11.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.11.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.11.2": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.11.3": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.11.4": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.11.5": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.12.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.12.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.12.2": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.12.3": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.13.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.13.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.14.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.14.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.14.2": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.14.3": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.14.4": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.15.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.15.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.16.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.17.0": {
      node_abi: 48,
      v8: "5.1"
    },
    "6.17.1": {
      node_abi: 48,
      v8: "5.1"
    },
    "7.0.0": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.1.0": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.2.0": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.2.1": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.3.0": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.4.0": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.5.0": {
      node_abi: 51,
      v8: "5.4"
    },
    "7.6.0": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.7.0": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.7.1": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.7.2": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.7.3": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.7.4": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.8.0": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.9.0": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.10.0": {
      node_abi: 51,
      v8: "5.5"
    },
    "7.10.1": {
      node_abi: 51,
      v8: "5.5"
    },
    "8.0.0": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.1.0": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.1.1": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.1.2": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.1.3": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.1.4": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.2.0": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.2.1": {
      node_abi: 57,
      v8: "5.8"
    },
    "8.3.0": {
      node_abi: 57,
      v8: "6.0"
    },
    "8.4.0": {
      node_abi: 57,
      v8: "6.0"
    },
    "8.5.0": {
      node_abi: 57,
      v8: "6.0"
    },
    "8.6.0": {
      node_abi: 57,
      v8: "6.0"
    },
    "8.7.0": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.8.0": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.8.1": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.9.0": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.9.1": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.9.2": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.9.3": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.9.4": {
      node_abi: 57,
      v8: "6.1"
    },
    "8.10.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.11.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.11.1": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.11.2": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.11.3": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.11.4": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.12.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.13.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.14.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.14.1": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.15.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.15.1": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.16.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.16.1": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.16.2": {
      node_abi: 57,
      v8: "6.2"
    },
    "8.17.0": {
      node_abi: 57,
      v8: "6.2"
    },
    "9.0.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.1.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.2.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.2.1": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.3.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.4.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.5.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.6.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.6.1": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.7.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.7.1": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.8.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.9.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.10.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.10.1": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.11.0": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.11.1": {
      node_abi: 59,
      v8: "6.2"
    },
    "9.11.2": {
      node_abi: 59,
      v8: "6.2"
    },
    "10.0.0": {
      node_abi: 64,
      v8: "6.6"
    },
    "10.1.0": {
      node_abi: 64,
      v8: "6.6"
    },
    "10.2.0": {
      node_abi: 64,
      v8: "6.6"
    },
    "10.2.1": {
      node_abi: 64,
      v8: "6.6"
    },
    "10.3.0": {
      node_abi: 64,
      v8: "6.6"
    },
    "10.4.0": {
      node_abi: 64,
      v8: "6.7"
    },
    "10.4.1": {
      node_abi: 64,
      v8: "6.7"
    },
    "10.5.0": {
      node_abi: 64,
      v8: "6.7"
    },
    "10.6.0": {
      node_abi: 64,
      v8: "6.7"
    },
    "10.7.0": {
      node_abi: 64,
      v8: "6.7"
    },
    "10.8.0": {
      node_abi: 64,
      v8: "6.7"
    },
    "10.9.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.10.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.11.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.12.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.13.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.14.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.14.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.14.2": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.15.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.15.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.15.2": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.15.3": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.16.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.16.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.16.2": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.16.3": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.17.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.18.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.18.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.19.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.20.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.20.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.21.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.22.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.22.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.23.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.23.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.23.2": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.23.3": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.24.0": {
      node_abi: 64,
      v8: "6.8"
    },
    "10.24.1": {
      node_abi: 64,
      v8: "6.8"
    },
    "11.0.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.1.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.2.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.3.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.4.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.5.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.6.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.7.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.8.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.9.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.10.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.10.1": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.11.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.12.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.13.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.14.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "11.15.0": {
      node_abi: 67,
      v8: "7.0"
    },
    "12.0.0": {
      node_abi: 72,
      v8: "7.4"
    },
    "12.1.0": {
      node_abi: 72,
      v8: "7.4"
    },
    "12.2.0": {
      node_abi: 72,
      v8: "7.4"
    },
    "12.3.0": {
      node_abi: 72,
      v8: "7.4"
    },
    "12.3.1": {
      node_abi: 72,
      v8: "7.4"
    },
    "12.4.0": {
      node_abi: 72,
      v8: "7.4"
    },
    "12.5.0": {
      node_abi: 72,
      v8: "7.5"
    },
    "12.6.0": {
      node_abi: 72,
      v8: "7.5"
    },
    "12.7.0": {
      node_abi: 72,
      v8: "7.5"
    },
    "12.8.0": {
      node_abi: 72,
      v8: "7.5"
    },
    "12.8.1": {
      node_abi: 72,
      v8: "7.5"
    },
    "12.9.0": {
      node_abi: 72,
      v8: "7.6"
    },
    "12.9.1": {
      node_abi: 72,
      v8: "7.6"
    },
    "12.10.0": {
      node_abi: 72,
      v8: "7.6"
    },
    "12.11.0": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.11.1": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.12.0": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.13.0": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.13.1": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.14.0": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.14.1": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.15.0": {
      node_abi: 72,
      v8: "7.7"
    },
    "12.16.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.16.1": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.16.2": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.16.3": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.17.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.18.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.18.1": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.18.2": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.18.3": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.18.4": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.19.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.19.1": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.20.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.20.1": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.20.2": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.21.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.0": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.1": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.2": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.3": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.4": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.5": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.6": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.7": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.8": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.9": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.10": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.11": {
      node_abi: 72,
      v8: "7.8"
    },
    "12.22.12": {
      node_abi: 72,
      v8: "7.8"
    },
    "13.0.0": {
      node_abi: 79,
      v8: "7.8"
    },
    "13.0.1": {
      node_abi: 79,
      v8: "7.8"
    },
    "13.1.0": {
      node_abi: 79,
      v8: "7.8"
    },
    "13.2.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.3.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.4.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.5.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.6.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.7.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.8.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.9.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.10.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.10.1": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.11.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.12.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.13.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "13.14.0": {
      node_abi: 79,
      v8: "7.9"
    },
    "14.0.0": {
      node_abi: 83,
      v8: "8.1"
    },
    "14.1.0": {
      node_abi: 83,
      v8: "8.1"
    },
    "14.2.0": {
      node_abi: 83,
      v8: "8.1"
    },
    "14.3.0": {
      node_abi: 83,
      v8: "8.1"
    },
    "14.4.0": {
      node_abi: 83,
      v8: "8.1"
    },
    "14.5.0": {
      node_abi: 83,
      v8: "8.3"
    },
    "14.6.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.7.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.8.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.9.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.10.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.10.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.11.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.12.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.13.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.13.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.14.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.15.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.15.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.15.2": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.15.3": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.15.4": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.15.5": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.16.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.16.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.2": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.3": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.4": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.5": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.17.6": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.18.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.18.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.18.2": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.18.3": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.19.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.19.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.19.2": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.19.3": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.20.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.20.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.21.0": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.21.1": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.21.2": {
      node_abi: 83,
      v8: "8.4"
    },
    "14.21.3": {
      node_abi: 83,
      v8: "8.4"
    },
    "15.0.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.0.1": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.1.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.2.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.2.1": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.3.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.4.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.5.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.5.1": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.6.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.7.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.8.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.9.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.10.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.11.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.12.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.13.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "15.14.0": {
      node_abi: 88,
      v8: "8.6"
    },
    "16.0.0": {
      node_abi: 93,
      v8: "9.0"
    },
    "16.1.0": {
      node_abi: 93,
      v8: "9.0"
    },
    "16.2.0": {
      node_abi: 93,
      v8: "9.0"
    },
    "16.3.0": {
      node_abi: 93,
      v8: "9.0"
    },
    "16.4.0": {
      node_abi: 93,
      v8: "9.1"
    },
    "16.4.1": {
      node_abi: 93,
      v8: "9.1"
    },
    "16.4.2": {
      node_abi: 93,
      v8: "9.1"
    },
    "16.5.0": {
      node_abi: 93,
      v8: "9.1"
    },
    "16.6.0": {
      node_abi: 93,
      v8: "9.2"
    },
    "16.6.1": {
      node_abi: 93,
      v8: "9.2"
    },
    "16.6.2": {
      node_abi: 93,
      v8: "9.2"
    },
    "16.7.0": {
      node_abi: 93,
      v8: "9.2"
    },
    "16.8.0": {
      node_abi: 93,
      v8: "9.2"
    },
    "16.9.0": {
      node_abi: 93,
      v8: "9.3"
    },
    "16.9.1": {
      node_abi: 93,
      v8: "9.3"
    },
    "16.10.0": {
      node_abi: 93,
      v8: "9.3"
    },
    "16.11.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.11.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.12.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.13.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.13.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.13.2": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.14.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.14.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.14.2": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.15.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.15.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.16.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.17.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.17.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.18.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.18.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.19.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.19.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.20.0": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.20.1": {
      node_abi: 93,
      v8: "9.4"
    },
    "16.20.2": {
      node_abi: 93,
      v8: "9.4"
    },
    "17.0.0": {
      node_abi: 102,
      v8: "9.5"
    },
    "17.0.1": {
      node_abi: 102,
      v8: "9.5"
    },
    "17.1.0": {
      node_abi: 102,
      v8: "9.5"
    },
    "17.2.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.3.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.3.1": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.4.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.5.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.6.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.7.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.7.1": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.7.2": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.8.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.9.0": {
      node_abi: 102,
      v8: "9.6"
    },
    "17.9.1": {
      node_abi: 102,
      v8: "9.6"
    },
    "18.0.0": {
      node_abi: 108,
      v8: "10.1"
    },
    "18.1.0": {
      node_abi: 108,
      v8: "10.1"
    },
    "18.2.0": {
      node_abi: 108,
      v8: "10.1"
    },
    "18.3.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.4.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.5.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.6.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.7.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.8.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.9.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.9.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.10.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.11.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.12.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.12.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.13.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.14.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.14.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.14.2": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.15.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.16.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.16.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.17.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.17.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.18.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.18.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.18.2": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.19.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.19.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.0": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.1": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.2": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.3": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.4": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.5": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.6": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.7": {
      node_abi: 108,
      v8: "10.2"
    },
    "18.20.8": {
      node_abi: 108,
      v8: "10.2"
    },
    "19.0.0": {
      node_abi: 111,
      v8: "10.7"
    },
    "19.0.1": {
      node_abi: 111,
      v8: "10.7"
    },
    "19.1.0": {
      node_abi: 111,
      v8: "10.7"
    },
    "19.2.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.3.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.4.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.5.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.6.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.6.1": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.7.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.8.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.8.1": {
      node_abi: 111,
      v8: "10.8"
    },
    "19.9.0": {
      node_abi: 111,
      v8: "10.8"
    },
    "20.0.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.1.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.2.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.3.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.3.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.4.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.5.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.5.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.6.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.6.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.7.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.8.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.8.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.9.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.10.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.11.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.11.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.12.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.12.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.12.2": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.13.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.13.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.14.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.15.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.15.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.16.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.17.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.18.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.18.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.18.2": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.18.3": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.19.0": {
      node_abi: 115,
      v8: "11.3"
    },
    "20.19.1": {
      node_abi: 115,
      v8: "11.3"
    },
    "21.0.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.1.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.2.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.3.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.4.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.5.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.6.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.6.1": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.6.2": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.7.0": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.7.1": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.7.2": {
      node_abi: 120,
      v8: "11.8"
    },
    "21.7.3": {
      node_abi: 120,
      v8: "11.8"
    },
    "22.0.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.1.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.2.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.3.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.4.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.4.1": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.5.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.5.1": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.6.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.7.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.8.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.9.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.10.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.11.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.12.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.13.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.13.1": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.14.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "22.15.0": {
      node_abi: 127,
      v8: "12.4"
    },
    "23.0.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.1.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.2.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.3.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.4.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.5.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.6.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.6.1": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.7.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.8.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.9.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.10.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "23.11.0": {
      node_abi: 131,
      v8: "12.9"
    },
    "24.0.0": {
      node_abi: 137,
      v8: "13.6"
    }
  };
});

// node_modules/@mapbox/node-pre-gyp/lib/util/versioning.js
var require_versioning = __commonJS((exports, module) => {
  module.exports = exports;
  var path = __require("path");
  var semver = require_semver2();
  var url = __require("url");
  var detect_libc = require_detect_libc();
  var napi = require_napi();
  var abi_crosswalk;
  if (process.env.NODE_PRE_GYP_ABI_CROSSWALK) {
    abi_crosswalk = __require(process.env.NODE_PRE_GYP_ABI_CROSSWALK);
  } else {
    abi_crosswalk = require_abi_crosswalk();
  }
  var major_versions = {};
  Object.keys(abi_crosswalk).forEach((v) => {
    const major = v.split(".")[0];
    if (!major_versions[major]) {
      major_versions[major] = v;
    }
  });
  function get_electron_abi(runtime, target_version) {
    if (!runtime) {
      throw new Error("get_electron_abi requires valid runtime arg");
    }
    if (typeof target_version === "undefined") {
      throw new Error("Empty target version is not supported if electron is the target.");
    }
    const sem_ver = semver.parse(target_version);
    return runtime + "-v" + sem_ver.major + "." + sem_ver.minor;
  }
  module.exports.get_electron_abi = get_electron_abi;
  function get_node_webkit_abi(runtime, target_version) {
    if (!runtime) {
      throw new Error("get_node_webkit_abi requires valid runtime arg");
    }
    if (typeof target_version === "undefined") {
      throw new Error("Empty target version is not supported if node-webkit is the target.");
    }
    return runtime + "-v" + target_version;
  }
  module.exports.get_node_webkit_abi = get_node_webkit_abi;
  function get_node_abi(runtime, versions) {
    if (!runtime) {
      throw new Error("get_node_abi requires valid runtime arg");
    }
    if (!versions) {
      throw new Error("get_node_abi requires valid process.versions object");
    }
    const sem_ver = semver.parse(versions.node);
    if (sem_ver.major === 0 && sem_ver.minor % 2) {
      return runtime + "-v" + versions.node;
    } else {
      return versions.modules ? runtime + "-v" + +versions.modules : "v8-" + versions.v8.split(".").slice(0, 2).join(".");
    }
  }
  module.exports.get_node_abi = get_node_abi;
  function get_runtime_abi(runtime, target_version) {
    if (!runtime) {
      throw new Error("get_runtime_abi requires valid runtime arg");
    }
    if (runtime === "node-webkit") {
      return get_node_webkit_abi(runtime, target_version || process.versions["node-webkit"]);
    } else if (runtime === "electron") {
      return get_electron_abi(runtime, target_version || process.versions.electron);
    } else {
      if (runtime !== "node") {
        throw new Error("Unknown Runtime: '" + runtime + "'");
      }
      if (!target_version) {
        return get_node_abi(runtime, process.versions);
      } else {
        let cross_obj;
        if (abi_crosswalk[target_version]) {
          cross_obj = abi_crosswalk[target_version];
        } else {
          const target_parts = target_version.split(".").map((i) => {
            return +i;
          });
          if (target_parts.length !== 3) {
            throw new Error("Unknown target version: " + target_version);
          }
          const major = target_parts[0];
          let minor = target_parts[1];
          let patch = target_parts[2];
          if (major === 1) {
            while (true) {
              if (minor > 0)
                --minor;
              if (patch > 0)
                --patch;
              const new_iojs_target = "" + major + "." + minor + "." + patch;
              if (abi_crosswalk[new_iojs_target]) {
                cross_obj = abi_crosswalk[new_iojs_target];
                console.log("Warning: node-pre-gyp could not find exact match for " + target_version);
                console.log("Warning: but node-pre-gyp successfully choose " + new_iojs_target + " as ABI compatible target");
                break;
              }
              if (minor === 0 && patch === 0) {
                break;
              }
            }
          } else if (major >= 2) {
            if (major_versions[major]) {
              cross_obj = abi_crosswalk[major_versions[major]];
              console.log("Warning: node-pre-gyp could not find exact match for " + target_version);
              console.log("Warning: but node-pre-gyp successfully choose " + major_versions[major] + " as ABI compatible target");
            }
          } else if (major === 0) {
            if (target_parts[1] % 2 === 0) {
              while (--patch > 0) {
                const new_node_target = "" + major + "." + minor + "." + patch;
                if (abi_crosswalk[new_node_target]) {
                  cross_obj = abi_crosswalk[new_node_target];
                  console.log("Warning: node-pre-gyp could not find exact match for " + target_version);
                  console.log("Warning: but node-pre-gyp successfully choose " + new_node_target + " as ABI compatible target");
                  break;
                }
              }
            }
          }
        }
        if (!cross_obj) {
          throw new Error("Unsupported target version: " + target_version);
        }
        const versions_obj = {
          node: target_version,
          v8: cross_obj.v8 + ".0",
          modules: cross_obj.node_abi > 1 ? cross_obj.node_abi : undefined
        };
        return get_node_abi(runtime, versions_obj);
      }
    }
  }
  module.exports.get_runtime_abi = get_runtime_abi;
  var required_parameters = [
    "module_name",
    "module_path",
    "host"
  ];
  function validate_config(package_json, opts) {
    const msg2 = package_json.name + ` package.json is not node-pre-gyp ready:
`;
    const missing = [];
    if (!package_json.main) {
      missing.push("main");
    }
    if (!package_json.version) {
      missing.push("version");
    }
    if (!package_json.name) {
      missing.push("name");
    }
    if (!package_json.binary) {
      missing.push("binary");
    }
    const o = package_json.binary;
    if (o) {
      required_parameters.forEach((p) => {
        if (!o[p] || typeof o[p] !== "string") {
          missing.push("binary." + p);
        }
      });
    }
    if (missing.length >= 1) {
      throw new Error(msg2 + `package.json must declare these properties: 
` + missing.join(`
`));
    }
    if (o) {
      const protocol = url.parse(o.host).protocol;
      if (protocol === "http:") {
        throw new Error("'host' protocol (" + protocol + ") is invalid - only 'https:' is accepted");
      }
    }
    napi.validate_package_json(package_json, opts);
  }
  module.exports.validate_config = validate_config;
  function eval_template(template, opts) {
    Object.keys(opts).forEach((key) => {
      const pattern = "{" + key + "}";
      while (template.indexOf(pattern) > -1) {
        template = template.replace(pattern, opts[key]);
      }
    });
    return template;
  }
  function fix_slashes(pathname) {
    if (pathname.slice(-1) !== "/") {
      return pathname + "/";
    }
    return pathname;
  }
  function drop_double_slashes(pathname) {
    return pathname.replace(/\/\//g, "/");
  }
  function get_process_runtime(versions) {
    let runtime = "node";
    if (versions["node-webkit"]) {
      runtime = "node-webkit";
    } else if (versions.electron) {
      runtime = "electron";
    }
    return runtime;
  }
  module.exports.get_process_runtime = get_process_runtime;
  var default_package_name = "{module_name}-v{version}-{node_abi}-{platform}-{arch}.tar.gz";
  var default_remote_path = "";
  module.exports.evaluate = function(package_json, options, napi_build_version) {
    options = options || {};
    validate_config(package_json, options);
    const v = package_json.version;
    const module_version = semver.parse(v);
    const runtime = options.runtime || get_process_runtime(process.versions);
    const opts = {
      name: package_json.name,
      configuration: options.debug ? "Debug" : "Release",
      debug: options.debug,
      module_name: package_json.binary.module_name,
      version: module_version.version,
      prerelease: module_version.prerelease.length ? module_version.prerelease.join(".") : "",
      build: module_version.build.length ? module_version.build.join(".") : "",
      major: module_version.major,
      minor: module_version.minor,
      patch: module_version.patch,
      runtime,
      node_abi: get_runtime_abi(runtime, options.target),
      node_abi_napi: napi.get_napi_version(options.target) ? "napi" : get_runtime_abi(runtime, options.target),
      napi_version: napi.get_napi_version(options.target),
      napi_build_version: napi_build_version || "",
      node_napi_label: napi_build_version ? "napi-v" + napi_build_version : get_runtime_abi(runtime, options.target),
      target: options.target || "",
      platform: options.target_platform || process.platform,
      target_platform: options.target_platform || process.platform,
      arch: options.target_arch || process.arch,
      target_arch: options.target_arch || process.arch,
      libc: options.target_libc || detect_libc.familySync() || "unknown",
      module_main: package_json.main,
      toolset: options.toolset || "",
      bucket: package_json.binary.bucket,
      region: package_json.binary.region,
      s3ForcePathStyle: package_json.binary.s3ForcePathStyle || false,
      acl: options.acl || package_json.binary.acl || "public-read"
    };
    const validModuleName = opts.module_name.replace("-", "_");
    const host = process.env["npm_config_" + validModuleName + "_binary_host_mirror"] || package_json.binary.host;
    opts.host = fix_slashes(eval_template(host, opts));
    opts.module_path = eval_template(package_json.binary.module_path, opts);
    if (options.module_root) {
      opts.module_path = path.join(options.module_root, opts.module_path);
    } else {
      opts.module_path = path.resolve(opts.module_path);
    }
    opts.module = path.join(opts.module_path, opts.module_name + ".node");
    opts.remote_path = package_json.binary.remote_path ? drop_double_slashes(fix_slashes(eval_template(package_json.binary.remote_path, opts))) : default_remote_path;
    const package_name = package_json.binary.package_name ? package_json.binary.package_name : default_package_name;
    opts.package_name = eval_template(package_name, opts);
    opts.staged_tarball = path.join("build/stage", opts.remote_path, opts.package_name);
    if (opts.s3ForcePathStyle) {
      opts.hosted_path = url.resolve(opts.host, drop_double_slashes(`${opts.bucket}/${opts.remote_path}`));
    } else {
      opts.hosted_path = url.resolve(opts.host, opts.remote_path);
    }
    opts.hosted_tarball = url.resolve(opts.hosted_path, opts.package_name);
    return opts;
  };
});

// node_modules/@mapbox/node-pre-gyp/lib/pre-binding.js
var require_pre_binding = __commonJS((exports, module) => {
  var npg = require_node_pre_gyp();
  var versioning = require_versioning();
  var napi = require_napi();
  var existsSync = __require("fs").existsSync || __require("path").existsSync;
  var path = __require("path");
  module.exports = exports;
  exports.usage = "Finds the require path for the node-pre-gyp installed module";
  exports.validate = function(package_json, opts) {
    versioning.validate_config(package_json, opts);
  };
  exports.find = function(package_json_path, opts) {
    if (!existsSync(package_json_path)) {
      throw new Error(package_json_path + "does not exist");
    }
    const prog = new npg.Run({ package_json_path, argv: process.argv });
    prog.setBinaryHostProperty();
    const package_json = prog.package_json;
    versioning.validate_config(package_json, opts);
    let napi_build_version;
    if (napi.get_napi_build_versions(package_json, opts)) {
      napi_build_version = napi.get_best_napi_build_version(package_json, opts);
    }
    opts = opts || {};
    if (!opts.module_root)
      opts.module_root = path.dirname(package_json_path);
    const meta = versioning.evaluate(package_json, opts, napi_build_version);
    return meta.module;
  };
});

// node_modules/@mapbox/node-pre-gyp/package.json
var require_package = __commonJS((exports, module) => {
  module.exports = {
    name: "@mapbox/node-pre-gyp",
    description: "Node.js native addon binary install tool",
    version: "2.0.3",
    keywords: [
      "native",
      "addon",
      "module",
      "c",
      "c++",
      "bindings",
      "binary"
    ],
    license: "BSD-3-Clause",
    author: "Dane Springmeyer <dane@mapbox.com>",
    repository: {
      type: "git",
      url: "git://github.com/mapbox/node-pre-gyp.git"
    },
    bin: "./bin/node-pre-gyp",
    main: "./lib/node-pre-gyp.js",
    engines: {
      node: ">=18"
    },
    dependencies: {
      consola: "^3.2.3",
      "detect-libc": "^2.0.0",
      "https-proxy-agent": "^7.0.5",
      "node-fetch": "^2.6.7",
      nopt: "^8.0.0",
      semver: "^7.5.3",
      tar: "^7.4.0"
    },
    devDependencies: {
      "@mapbox/cloudfriend": "^9.0.0",
      "@mapbox/eslint-config-mapbox": "^5.0.1",
      "aws-sdk": "^2.1087.0",
      codecov: "^3.8.3",
      eslint: "^8.57.0",
      "eslint-plugin-n": "^17.9.0",
      "mock-aws-s3": "^4.0.2",
      nock: "^13.5.4",
      "node-addon-api": "^8.1.0",
      nyc: "^17.0.0",
      tape: "^5.5.2",
      "tar-fs": "^3.1.1"
    },
    nyc: {
      all: true,
      "skip-full": false,
      exclude: [
        "test/**"
      ]
    },
    scripts: {
      coverage: "nyc --all --include index.js --include lib/ npm test",
      "upload-coverage": "nyc report --reporter json && codecov --clear --flags=unit --file=./coverage/coverage-final.json",
      lint: "eslint bin/node-pre-gyp lib/*js lib/util/*js test/*js scripts/*js",
      fix: "npm run lint -- --fix",
      "update-crosswalk": "node scripts/abi_crosswalk.js",
      test: "tape test/*test.js",
      "test:s3": "tape test/s3.test.js",
      bucket: "node scripts/set-bucket.js"
    },
    overrides: {
      "js-yaml": "^3.14.2"
    }
  };
});

// node_modules/@mapbox/node-pre-gyp/lib/node-pre-gyp.js
var require_node_pre_gyp = __commonJS((exports, module) => {
  var __dirname = "/home/seamu/Coding/1_Repos/Personal/TeleMU/TeleMU/node_modules/@mapbox/node-pre-gyp/lib";
  module.exports = exports;
  var fs = __require("fs");
  var path = __require("path");
  var nopt = require_nopt();
  var log = require_log();
  var napi = require_napi();
  var EE = __require("events").EventEmitter;
  var inherits = __require("util").inherits;
  var cli_commands = [
    "clean",
    "install",
    "reinstall",
    "build",
    "rebuild",
    "package",
    "testpackage",
    "publish",
    "unpublish",
    "info",
    "testbinary",
    "reveal",
    "configure"
  ];
  var aliases = {};
  Object.defineProperty(exports, "find", {
    get: function() {
      return require_pre_binding().find;
    },
    enumerable: true
  });
  function Run({ package_json_path = "./package.json", argv }) {
    this.package_json_path = package_json_path;
    this.commands = {};
    const self = this;
    cli_commands.forEach((command) => {
      self.commands[command] = function(argvx, callback) {
        log.verbose("command", command, argvx);
        return __require("./" + command)(self, argvx, callback);
      };
    });
    this.parseArgv(argv);
    this.binaryHostSet = false;
  }
  inherits(Run, EE);
  exports.Run = Run;
  var proto = Run.prototype;
  proto.package = require_package();
  proto.configDefs = {
    help: Boolean,
    arch: String,
    debug: Boolean,
    directory: String,
    proxy: String,
    loglevel: String,
    acl: String
  };
  proto.shorthands = {
    release: "--no-debug",
    C: "--directory",
    debug: "--debug",
    j: "--jobs",
    silent: "--loglevel=silent",
    silly: "--loglevel=silly",
    verbose: "--loglevel=verbose"
  };
  proto.aliases = aliases;
  proto.parseArgv = function parseOpts(argv) {
    this.opts = nopt(this.configDefs, this.shorthands, argv);
    this.argv = this.opts.argv.remain.slice();
    const commands = this.todo = [];
    argv = this.argv.map((arg) => {
      if (arg in this.aliases) {
        arg = this.aliases[arg];
      }
      return arg;
    });
    argv.slice().forEach((arg) => {
      if (arg in this.commands) {
        const args = argv.splice(0, argv.indexOf(arg));
        argv.shift();
        if (commands.length > 0) {
          commands[commands.length - 1].args = args;
        }
        commands.push({ name: arg, args: [] });
      }
    });
    if (commands.length > 0) {
      commands[commands.length - 1].args = argv.splice(0);
    }
    let package_json_path = this.package_json_path;
    if (this.opts.directory) {
      package_json_path = path.join(this.opts.directory, package_json_path);
    }
    this.package_json = JSON.parse(fs.readFileSync(package_json_path));
    this.todo = napi.expand_commands(this.package_json, this.opts, commands);
    const npm_config_prefix = "npm_config_";
    Object.keys(process.env).forEach((name) => {
      if (name.indexOf(npm_config_prefix) !== 0)
        return;
      const val = process.env[name];
      if (name === npm_config_prefix + "loglevel") {
        log.level = val;
      } else {
        name = name.substring(npm_config_prefix.length);
        if (name === "argv") {
          if (this.opts.argv && this.opts.argv.remain && this.opts.argv.remain.length) {} else {
            this.opts[name] = val;
          }
        } else {
          this.opts[name] = val;
        }
      }
    });
    if (this.opts.loglevel) {
      log.level = this.opts.loglevel;
    }
    log.resume();
  };
  proto.setBinaryHostProperty = function(command) {
    if (this.binaryHostSet) {
      return this.package_json.binary.host;
    }
    const p = this.package_json;
    if (!p || !p.binary || p.binary.host) {
      return "";
    }
    if (!p.binary.staging_host || !p.binary.production_host) {
      return "";
    }
    let target = "production_host";
    if (command === "publish" || command === "unpublish") {
      target = "staging_host";
    }
    const npg_s3_host = process.env.node_pre_gyp_s3_host;
    if (npg_s3_host === "staging" || npg_s3_host === "production") {
      target = `${npg_s3_host}_host`;
    } else if (this.opts["s3_host"] === "staging" || this.opts["s3_host"] === "production") {
      target = `${this.opts["s3_host"]}_host`;
    } else if (this.opts["s3_host"] || npg_s3_host) {
      throw new Error(`invalid s3_host ${this.opts["s3_host"] || npg_s3_host}`);
    }
    p.binary.host = p.binary[target];
    this.binaryHostSet = true;
    return p.binary.host;
  };
  proto.usage = function usage() {
    const str = [
      "",
      "  Usage: node-pre-gyp <command> [options]",
      "",
      "  where <command> is one of:",
      cli_commands.map((c) => {
        return "    - " + c + " - " + __require("./" + c).usage;
      }).join(`
`),
      "",
      "node-pre-gyp@" + this.version + "  " + path.resolve(__dirname, ".."),
      "node@" + process.versions.node
    ].join(`
`);
    return str;
  };
  Object.defineProperty(proto, "version", {
    get: function() {
      return this.package.version;
    },
    enumerable: true
  });
});

// node_modules/duckdb/lib/duckdb-binding.js
var require_duckdb_binding = __commonJS((exports, module) => {
  var __dirname = "/home/seamu/Coding/1_Repos/Personal/TeleMU/TeleMU/node_modules/duckdb/lib";
  var binary = require_node_pre_gyp();
  var path = __require("path");
  var binding_path = binary.find(path.resolve(path.join(__dirname, "../package.json")));
  var binding = __require(binding_path);
  module.exports = exports = binding;
});

// node_modules/duckdb/lib/duckdb.js
var require_duckdb = __commonJS((exports, module) => {
  var duckdb = require_duckdb_binding();
  module.exports = exports = duckdb;
  var ERROR = duckdb.ERROR;
  var OPEN_READONLY = duckdb.OPEN_READONLY;
  var OPEN_READWRITE = duckdb.OPEN_READWRITE;
  var OPEN_CREATE = duckdb.OPEN_CREATE;
  var OPEN_FULLMUTEX = duckdb.OPEN_FULLMUTEX;
  var OPEN_SHAREDCACHE = duckdb.OPEN_SHAREDCACHE;
  var OPEN_PRIVATECACHE = duckdb.OPEN_PRIVATECACHE;
  var Database = duckdb.Database;
  var Connection = duckdb.Connection;
  var Statement = duckdb.Statement;
  var QueryResult = duckdb.QueryResult;
  var TokenType = duckdb.TokenType;
  QueryResult.prototype.nextChunk;
  QueryResult.prototype.nextIpcBuffer;
  QueryResult.prototype[Symbol.asyncIterator] = async function* () {
    let prefetch = this.nextChunk();
    while (true) {
      const chunk = await prefetch;
      if (!chunk) {
        return;
      }
      prefetch = this.nextChunk();
      for (const row of chunk) {
        yield row;
      }
    }
  };
  Connection.prototype.run = function(sql) {
    var statement = new Statement(this, sql);
    return statement.run.apply(statement, arguments);
  };
  Connection.prototype.all = function(sql) {
    var statement = new Statement(this, sql);
    return statement.all.apply(statement, arguments);
  };

  class IpcResultStreamIterator {
    constructor(stream_result_p) {
      this._depleted = false;
      this.stream_result = stream_result_p;
    }
    async next() {
      if (this._depleted) {
        return { done: true, value: null };
      }
      const ipc_raw = await this.stream_result.nextIpcBuffer();
      const res = new Uint8Array(ipc_raw);
      this._depleted = res.length == 0;
      return {
        done: this._depleted,
        value: res
      };
    }
    [Symbol.asyncIterator]() {
      return this;
    }
    async toArray() {
      const retval = [];
      for await (const ipc_buf of this) {
        retval.push(ipc_buf);
      }
      retval.push(new Uint8Array([0, 0, 0, 0]));
      return retval;
    }
  }
  Connection.prototype.arrowIPCAll = function(sql) {
    const query = "SELECT * FROM to_arrow_ipc((" + sql + "));";
    var statement = new Statement(this, query);
    return statement.arrowIPCAll.apply(statement, arguments);
  };
  Connection.prototype.arrowIPCStream = async function(sql) {
    const query = "SELECT * FROM to_arrow_ipc((" + sql + "));";
    const statement = new Statement(this, query);
    return new IpcResultStreamIterator(await statement.stream.apply(statement, arguments));
  };
  Connection.prototype.each = function(sql) {
    var statement = new Statement(this, sql);
    return statement.each.apply(statement, arguments);
  };
  Connection.prototype.stream = async function* (sql) {
    const statement = new Statement(this, sql);
    const queryResult = await statement.stream.apply(statement, arguments);
    for await (const result of queryResult) {
      yield result;
    }
  };
  Connection.prototype.register_udf = function(name, return_type, fun) {
    return this.register_udf_bulk(name, return_type, function(desc) {
      try {
        const buildResolver = (arg) => {
          let validity = arg.validity || null;
          switch (arg.physicalType) {
            case "STRUCT": {
              const tmp = {};
              const children = [];
              for (let j = 0;j < (arg.children.length || 0); ++j) {
                const attr = arg.children[j];
                const child = buildResolver(attr);
                children.push((row) => {
                  tmp[attr.name] = child(row);
                });
              }
              if (validity != null) {
                return (row) => {
                  if (!validity[row]) {
                    return null;
                  }
                  for (const resolver of children) {
                    resolver(row);
                  }
                  return tmp;
                };
              } else {
                return (row) => {
                  for (const resolver of children) {
                    resolver(row);
                  }
                  return tmp;
                };
              }
            }
            default: {
              if (arg.data === undefined) {
                throw new Error("malformed data view, expected data buffer for argument of type: " + arg.physicalType);
              }
              const data = arg.data;
              if (validity != null) {
                return (row) => !validity[row] ? null : data[row];
              } else {
                return (row) => data[row];
              }
            }
          }
        };
        const argResolvers = [];
        for (let i = 0;i < desc.args.length; ++i) {
          argResolvers.push(buildResolver(desc.args[i]));
        }
        const args = [];
        for (let i = 0;i < desc.args.length; ++i) {
          args.push(null);
        }
        desc.ret.validity = new Uint8Array(desc.rows);
        switch (desc.ret.physicalType) {
          case "INT8":
            desc.ret.data = new Int8Array(desc.rows);
            break;
          case "INT16":
            desc.ret.data = new Int16Array(desc.rows);
            break;
          case "INT32":
            desc.ret.data = new Int32Array(desc.rows);
            break;
          case "DOUBLE":
            desc.ret.data = new Float64Array(desc.rows);
            break;
          case "DATE64":
          case "TIME64":
          case "TIMESTAMP":
          case "INT64":
            desc.ret.data = new BigInt64Array(desc.rows);
            break;
          case "UINT64":
            desc.ret.data = new BigUint64Array(desc.rows);
            break;
          case "BLOB":
          case "VARCHAR":
            desc.ret.data = new Array(desc.rows);
            break;
        }
        for (let i = 0;i < desc.rows; ++i) {
          for (let j = 0;j < desc.args.length; ++j) {
            args[j] = argResolvers[j](i);
          }
          const res = fun(...args);
          desc.ret.data[i] = res;
          desc.ret.validity[i] = res === undefined || res === null ? 0 : 1;
        }
      } catch (error) {
        msg = error;
        if (typeof error == "object" && "message" in error) {
          msg = error.message;
        }
        throw { name: "DuckDB-UDF-Exception", message: msg };
      }
    });
  };
  Connection.prototype.prepare;
  Connection.prototype.exec;
  Connection.prototype.register_udf_bulk;
  Connection.prototype.unregister_udf;
  var default_connection = function(o) {
    if (o.default_connection == undefined) {
      o.default_connection = new duckdb.Connection(o);
    }
    return o.default_connection;
  };
  Connection.prototype.register_buffer;
  Connection.prototype.unregister_buffer;
  Connection.prototype.close;
  Database.prototype.close = function() {
    if (this.default_connection) {
      this.default_connection.close();
      this.default_connection = null;
    }
    this.close_internal.apply(this, arguments);
  };
  Database.prototype.close_internal;
  Database.prototype.wait;
  Database.prototype.serialize;
  Database.prototype.parallelize;
  Database.prototype.connect;
  Database.prototype.interrupt;
  Database.prototype.prepare = function() {
    return default_connection(this).prepare.apply(this.default_connection, arguments);
  };
  Database.prototype.run = function() {
    default_connection(this).run.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.scanArrowIpc = function() {
    default_connection(this).scanArrowIpc.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.each = function() {
    default_connection(this).each.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.stream = function() {
    return default_connection(this).stream.apply(this.default_connection, arguments);
  };
  Database.prototype.all = function() {
    default_connection(this).all.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.arrowIPCAll = function() {
    default_connection(this).arrowIPCAll.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.arrowIPCStream = function() {
    return default_connection(this).arrowIPCStream.apply(this.default_connection, arguments);
  };
  Database.prototype.exec = function() {
    default_connection(this).exec.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.register_udf = function() {
    default_connection(this).register_udf.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.register_buffer = function() {
    default_connection(this).register_buffer.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.unregister_buffer = function() {
    default_connection(this).unregister_buffer.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.unregister_udf = function() {
    default_connection(this).unregister_udf.apply(this.default_connection, arguments);
    return this;
  };
  Database.prototype.registerReplacementScan;
  Database.prototype.tokenize;
  Database.prototype.get = function() {
    throw "get() is not implemented because it's evil";
  };
  Statement.prototype.get = function() {
    throw "get() is not implemented because it's evil";
  };
  Statement.prototype.run;
  Statement.prototype.all;
  Statement.prototype.arrowIPCAll;
  Statement.prototype.each;
  Statement.prototype.finalize;
  Statement.prototype.stream;
  Statement.prototype.sql;
  Statement.prototype.columns;
});

// node_modules/electrobun/dist/api/bun/index.ts
init_eventEmitter();
await __promiseAll([
  init_BrowserWindow(),
  init_BrowserView(),
  init_Tray()
]);

// node_modules/electrobun/dist/api/bun/core/ApplicationMenu.ts
init_eventEmitter();
await init_native();

// node_modules/electrobun/dist/api/bun/core/ContextMenu.ts
init_eventEmitter();
await init_native();

// node_modules/electrobun/dist/api/bun/index.ts
init_Paths();
init_BuildConfig();
await __promiseAll([
  init_Updater(),
  init_Utils(),
  init_Socket(),
  init_native()
]);

// src/bun/db.ts
var import_duckdb = __toESM(require_duckdb(), 1);
var _NUMERIC_TYPE_FRAGMENTS = [
  "INT",
  "FLOAT",
  "DOUBLE",
  "DECIMAL",
  "NUMERIC",
  "BIGINT",
  "SMALL",
  "TINY",
  "HUGEINT",
  "REAL"
];
function isNumericType(colType) {
  const upper = colType.toUpperCase();
  return _NUMERIC_TYPE_FRAGMENTS.some((t) => upper.includes(t));
}
function dbAll(db, sql, params = []) {
  return new Promise((resolve3, reject) => {
    db.all(sql, ...params, (err, rows) => {
      if (err)
        reject(err);
      else
        resolve3(rows ?? []);
    });
  });
}
function dbRun(db, sql, params = []) {
  return new Promise((resolve3, reject) => {
    db.run(sql, ...params, (err) => {
      if (err)
        reject(err);
      else
        resolve3();
    });
  });
}
var _db = null;
function connect(dbPath) {
  return new Promise((resolve3, reject) => {
    _db = new import_duckdb.default.Database(dbPath, { access_mode: "READ_ONLY" }, (err) => {
      if (err) {
        _db = null;
        reject(err);
      } else {
        resolve3();
      }
    });
  });
}
function disconnect() {
  if (_db) {
    _db.close();
    _db = null;
  }
}
function getDb() {
  if (!_db)
    throw new Error("No database connection");
  return _db;
}
async function listTables() {
  const rows = await dbAll(getDb(), "SHOW TABLES");
  return rows.map((r) => String(Object.values(r)[0]));
}
async function tableRowCount(table) {
  const rows = await dbAll(getDb(), `SELECT COUNT(*) AS cnt FROM "${table}"`);
  return Number(rows[0]?.cnt ?? 0);
}
async function listTablesWithCounts() {
  const tables = await listTables();
  const result = [];
  for (const name of tables) {
    const rowCount = await tableRowCount(name);
    result.push({ name, rowCount });
  }
  return result;
}
async function tableSchema(table) {
  const rows = await dbAll(getDb(), `PRAGMA table_info('${table}')`);
  return rows.map((r) => ({
    name: String(r.name),
    type: String(r.type),
    nullable: r.notnull === "YES" || r.notnull === false
  }));
}
async function columnStats(table, column, colType) {
  const stats = {
    column,
    type: colType,
    nulls: 0,
    distinct: 0,
    min: null,
    max: null,
    avg: null
  };
  const countRows = await dbAll(getDb(), `SELECT COUNT(*) FILTER (WHERE "${column}" IS NULL) AS nulls, COUNT(DISTINCT "${column}") AS dist FROM "${table}"`);
  stats.nulls = Number(countRows[0]?.nulls ?? 0);
  stats.distinct = Number(countRows[0]?.dist ?? 0);
  if (isNumericType(colType)) {
    const aggRows = await dbAll(getDb(), `SELECT MIN("${column}") AS mn, MAX("${column}") AS mx, AVG("${column}") AS avg FROM "${table}"`);
    const row = aggRows[0];
    if (row) {
      stats.min = row.mn != null ? Number(row.mn) : null;
      stats.max = row.mx != null ? Number(row.mx) : null;
      stats.avg = row.avg != null ? Math.round(Number(row.avg) * 1e4) / 1e4 : null;
    }
  }
  return stats;
}
async function allColumnStats(table) {
  const schema = await tableSchema(table);
  const results = [];
  for (const col of schema) {
    results.push(await columnStats(table, col.name, col.type));
  }
  return results;
}
async function previewTable(table, limit = 100) {
  const rows = await dbAll(getDb(), `SELECT * FROM "${table}" LIMIT ${limit}`);
  if (rows.length === 0)
    return { columns: [], rows: [] };
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c]))
  };
}
async function filteredPreview(table, filters, limit = 100) {
  const clauses = [];
  const params = [];
  for (const [col, pattern] of Object.entries(filters)) {
    if (pattern.trim()) {
      clauses.push(`CAST("${col}" AS VARCHAR) ILIKE ?`);
      params.push(`%${pattern}%`);
    }
  }
  const where = clauses.length > 0 ? ` WHERE ${clauses.join(" AND ")}` : "";
  const sql = `SELECT * FROM "${table}"${where} LIMIT ${limit}`;
  const rows = await dbAll(getDb(), sql, params);
  if (rows.length === 0) {
    const schema = await tableSchema(table);
    return { columns: schema.map((c) => c.name), rows: [] };
  }
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c]))
  };
}
async function executeSql(sql) {
  const rows = await dbAll(getDb(), sql);
  if (rows.length === 0)
    return { columns: [], rows: [] };
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c]))
  };
}
async function numericColumns(table) {
  const schema = await tableSchema(table);
  return schema.filter((c) => isNumericType(c.type)).map((c) => c.name);
}
async function allNumericColumns(tables) {
  const result = {};
  for (const t of tables) {
    result[t] = await numericColumns(t);
  }
  return result;
}
async function fetchColumns(table, columns) {
  const cols = columns.map((c) => `"${c}"`).join(", ");
  const sql = `SELECT ${cols} FROM "${table}"`;
  const rows = await dbAll(getDb(), sql);
  if (rows.length === 0)
    return { columns, rows: [] };
  const resultCols = Object.keys(rows[0]);
  return {
    columns: resultCols,
    rows: rows.map((r) => resultCols.map((c) => r[c]))
  };
}
async function fetchJoinedColumns(tableColumns, on = "ts") {
  const allTables = Object.keys(tableColumns);
  if (allTables.length === 0)
    return { columns: [], rows: [] };
  const tables = [];
  for (const tbl of allTables) {
    const schema = await tableSchema(tbl);
    if (schema.some((c) => c.name === on)) {
      tables.push(tbl);
    }
  }
  if (tables.length === 0)
    return { columns: [], rows: [] };
  const selects = [`"${tables[0]}"."${on}" AS "${on}"`];
  for (const tbl of tables) {
    const cols = tableColumns[tbl];
    if (!cols)
      continue;
    for (const col of cols) {
      if (col === on)
        continue;
      selects.push(`"${tbl}"."${col}" AS "${tbl}.${col}"`);
    }
  }
  let fromClause = `"${tables[0]}"`;
  for (let i = 1;i < tables.length; i++) {
    fromClause += ` INNER JOIN "${tables[i]}" ON "${tables[0]}"."${on}" = "${tables[i]}"."${on}"`;
  }
  const sql = `SELECT ${selects.join(", ")} FROM ${fromClause}`;
  const rows = await dbAll(getDb(), sql);
  if (rows.length === 0)
    return { columns: [], rows: [] };
  const columns = Object.keys(rows[0]);
  return {
    columns,
    rows: rows.map((r) => columns.map((c) => r[c]))
  };
}
async function exportCsv(outputPath, table, sql) {
  if (sql) {
    await dbRun(getDb(), `COPY (${sql}) TO '${outputPath}' (FORMAT CSV, HEADER)`);
  } else if (table) {
    await dbRun(getDb(), `COPY "${table}" TO '${outputPath}' (FORMAT CSV, HEADER)`);
  }
}
async function exportJson(outputPath, table, sql) {
  if (sql) {
    await dbRun(getDb(), `COPY (${sql}) TO '${outputPath}' (FORMAT JSON)`);
  } else if (table) {
    await dbRun(getDb(), `COPY "${table}" TO '${outputPath}' (FORMAT JSON)`);
  }
}

// src/bun/index.ts
import { join as join5 } from "path";
var DEV_SERVER_PORT = 5173;
var DEV_SERVER_URL = `http://localhost:${DEV_SERVER_PORT}`;
async function getMainViewUrl() {
  const channel = await Updater.localInfo.channel();
  if (channel === "dev") {
    try {
      await fetch(DEV_SERVER_URL, { method: "HEAD" });
      console.log(`HMR enabled: Using Vite dev server at ${DEV_SERVER_URL}`);
      return DEV_SERVER_URL;
    } catch {
      console.log("Vite dev server not running. Run 'bun run dev:hmr' for HMR support.");
    }
  }
  return "views://mainview/index.html";
}
var url = await getMainViewUrl();
var rpc = BrowserView.defineRPC({
  handlers: {
    requests: {
      openFileDialog: async () => {
        const paths2 = await exports_Utils.openFileDialog({
          startingFolder: "~/",
          allowedFileTypes: "*",
          canChooseFiles: true,
          canChooseDirectory: false,
          allowsMultipleSelection: false
        });
        return paths2.length > 0 && paths2[0] !== "" ? paths2[0] : null;
      },
      saveFileDialog: async (params) => {
        const paths2 = await exports_Utils.openFileDialog({
          startingFolder: "~/",
          allowedFileTypes: "*",
          canChooseFiles: false,
          canChooseDirectory: true,
          allowsMultipleSelection: false
        });
        if (paths2.length > 0 && paths2[0] !== "") {
          return join5(paths2[0], params.defaultName);
        }
        return null;
      },
      connect: async (params) => {
        console.log("[RPC] connect called with path:", params.path);
        await connect(params.path);
        console.log("[RPC] db.connect resolved");
        const tables = await listTablesWithCounts();
        console.log("[RPC] listTablesWithCounts returned", tables.length, "tables");
        return { tables };
      },
      disconnect: () => {
        disconnect();
      },
      tableSchema: async (params) => {
        return tableSchema(params.table);
      },
      allColumnStats: async (params) => {
        return allColumnStats(params.table);
      },
      previewTable: async (params) => {
        return previewTable(params.table, params.limit);
      },
      filteredPreview: async (params) => {
        return filteredPreview(params.table, params.filters, params.limit);
      },
      executeSql: async (params) => {
        return executeSql(params.sql);
      },
      allNumericColumns: async (params) => {
        return allNumericColumns(params.tables);
      },
      fetchColumns: async (params) => {
        return fetchColumns(params.table, params.columns);
      },
      fetchJoinedColumns: async (params) => {
        return fetchJoinedColumns(params.tableColumns, params.on);
      },
      exportCsv: async (params) => {
        await exportCsv(params.outputPath, params.table, params.sql);
      },
      exportJson: async (params) => {
        await exportJson(params.outputPath, params.table, params.sql);
      }
    },
    messages: {}
  },
  maxRequestTime: 300000
});
var mainWindow = new BrowserWindow({
  title: "TeleMU \u2014 Telemetry Explorer",
  url,
  frame: {
    width: 1280,
    height: 800,
    x: 100,
    y: 100
  },
  rpc
});
console.log("TeleMU \u2014 Telemetry Explorer started!");
