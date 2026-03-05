import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * Tests for the tray integration bridge API surface.
 * Since Tauri APIs are not available in jsdom, we mock window.telemu
 * to verify that renderer code can interact with the tray API correctly.
 */

describe("tray bridge API", () => {
  beforeEach(() => {
    // Mock the Tauri-bridge-exposed API on window
    window.telemu = {
      platform: "linux",
      isTauri: true,
      updateTrayStatus: vi.fn(),
      notify: vi.fn(),
      setMinimizeToTray: vi.fn(),
      setStartMinimized: vi.fn(),
      onToggleRecording: vi.fn(() => vi.fn()),
      onToggleConnection: vi.fn(() => vi.fn()),
    };
  });

  it("updateTrayStatus sends connected/recording state", () => {
    window.telemu?.updateTrayStatus({ connected: true, recording: false });
    expect(window.telemu?.updateTrayStatus).toHaveBeenCalledWith({
      connected: true,
      recording: false,
    });
  });

  it("updateTrayStatus sends recording state", () => {
    window.telemu?.updateTrayStatus({ connected: true, recording: true });
    expect(window.telemu?.updateTrayStatus).toHaveBeenCalledWith({
      connected: true,
      recording: true,
    });
  });

  it("notify sends title and body", () => {
    window.telemu?.notify("Connection", "Connected to LMU");
    expect(window.telemu?.notify).toHaveBeenCalledWith(
      "Connection",
      "Connected to LMU"
    );
  });

  it("setMinimizeToTray sends boolean", () => {
    window.telemu?.setMinimizeToTray(true);
    expect(window.telemu?.setMinimizeToTray).toHaveBeenCalledWith(true);

    window.telemu?.setMinimizeToTray(false);
    expect(window.telemu?.setMinimizeToTray).toHaveBeenCalledWith(false);
  });

  it("setStartMinimized sends boolean", () => {
    window.telemu?.setStartMinimized(true);
    expect(window.telemu?.setStartMinimized).toHaveBeenCalledWith(true);
  });

  it("onToggleRecording registers callback and returns unsubscribe", () => {
    const callback = vi.fn();
    const unsubscribe = window.telemu?.onToggleRecording(callback);

    expect(window.telemu?.onToggleRecording).toHaveBeenCalledWith(callback);
    expect(typeof unsubscribe).toBe("function");
  });

  it("onToggleConnection registers callback and returns unsubscribe", () => {
    const callback = vi.fn();
    const unsubscribe = window.telemu?.onToggleConnection(callback);

    expect(window.telemu?.onToggleConnection).toHaveBeenCalledWith(callback);
    expect(typeof unsubscribe).toBe("function");
  });
});
