import { describe, it, expect } from "vitest";
import { useTelemetryStore } from "../src/stores/telemetryStore";

describe("telemetryStore", () => {
  it("pushes channel data and maintains history", () => {
    const store = useTelemetryStore.getState();
    store.pushChannels({ speed: 100, rpm: 5000 });

    const state = useTelemetryStore.getState();
    expect(state.channels.speed?.value).toBe(100);
    expect(state.channels.rpm?.value).toBe(5000);
    expect(state.channels.speed?.history).toEqual([100]);
  });

  it("sets status", () => {
    const store = useTelemetryStore.getState();
    store.setStatus({
      type: "status",
      drs: true,
      pit: false,
      flag: 0,
      tc: false,
      abs: false,
    });

    const state = useTelemetryStore.getState();
    expect(state.status.drs).toBe(true);
  });
});
