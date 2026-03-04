/// <reference types="vite/client" />

interface Window {
  telemu?: {
    platform: string;
    isElectron: boolean;

    /** Update tray icon/menu to reflect current status. */
    updateTrayStatus: (status: { connected: boolean; recording: boolean }) => void;
    /** Show a native OS notification via the tray. */
    notify: (title: string, body: string) => void;
    /** Set whether closing the window minimizes to tray. */
    setMinimizeToTray: (value: boolean) => void;
    /** Set whether the app starts minimized to tray. */
    setStartMinimized: (value: boolean) => void;

    /** Listen for tray menu "toggle recording" action. Returns unsubscribe fn. */
    onToggleRecording: (callback: () => void) => () => void;
    /** Listen for tray menu "toggle connection" action. Returns unsubscribe fn. */
    onToggleConnection: (callback: () => void) => () => void;
  };
}
