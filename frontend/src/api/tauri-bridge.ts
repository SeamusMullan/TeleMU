/**
 * Tauri bridge — implements the window.telemu API surface using Tauri APIs.
 *
 * Call `initTauriBridge()` once at app startup (main.tsx). Afterwards the
 * rest of the codebase can use `window.telemu?.*` as before.
 */

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { sendNotification, isPermissionGranted, requestPermission } from "@tauri-apps/plugin-notification";

/** Whether the app is running inside a Tauri shell. */
export const isTauriEnv: boolean =
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

export async function initTauriBridge(): Promise<void> {
  if (!isTauriEnv) return;

  // Ensure notification permission is granted (best-effort)
  let permissionGranted = await isPermissionGranted();
  if (!permissionGranted) {
    const permission = await requestPermission();
    permissionGranted = permission === "granted";
  }

  window.telemu = {
    platform: navigator.platform,
    isTauri: true,

    updateTrayStatus: (status) => {
      invoke("update_tray_status", {
        connected: status.connected,
        recording: status.recording,
      }).catch(console.error);
    },

    notify: (title, body) => {
      if (permissionGranted) {
        sendNotification({ title, body });
      }
    },

    setMinimizeToTray: (value) => {
      invoke("set_minimize_to_tray", { value }).catch(console.error);
    },

    setStartMinimized: (value) => {
      invoke("set_start_minimized", { value }).catch(console.error);
    },

    onToggleRecording: (callback) => {
      let unlisten: (() => void) | null = null;
      listen("tray://toggle-recording", () => callback()).then((fn) => {
        unlisten = fn;
      });
      return () => { unlisten?.(); };
    },

    onToggleConnection: (callback) => {
      let unlisten: (() => void) | null = null;
      listen("tray://toggle-connection", () => callback()).then((fn) => {
        unlisten = fn;
      });
      return () => { unlisten?.(); };
    },
  };
}
