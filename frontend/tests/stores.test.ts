import { describe, it, expect } from "vitest";
import { useTelemetryStore } from "../src/stores/telemetryStore";
import { useRecordingStore } from "../src/stores/recordingStore";

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

describe("recordingStore", () => {
  it("starts idle", () => {
    const state = useRecordingStore.getState();
    expect(state.active).toBe(false);
    expect(state.filename).toBe("");
  });

  it("updates status via setStatus", () => {
    const store = useRecordingStore.getState();
    store.setStatus({
      active: true,
      filename: "test.tmu",
      output_path: "/tmp/test.tmu",
      duration_seconds: 5,
      file_size_bytes: 1024,
      data_rate_bps: 512,
    });

    const state = useRecordingStore.getState();
    expect(state.active).toBe(true);
    expect(state.filename).toBe("test.tmu");
    expect(state.duration_seconds).toBe(5);
  });

  it("updates output directory", () => {
    const store = useRecordingStore.getState();
    store.setOutputDir("/custom/dir");
    expect(useRecordingStore.getState().outputDir).toBe("/custom/dir");
  });
});
