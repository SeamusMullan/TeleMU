/** Recording state — tracks active recording, timer, file size, data rate. */

import { create } from "zustand";
import type { RecordingStatus } from "../api/types";

interface RecordingState extends RecordingStatus {
  outputDir: string;

  setStatus: (s: RecordingStatus) => void;
  setOutputDir: (dir: string) => void;
}

const INITIAL: RecordingStatus = {
  active: false,
  filename: "",
  output_path: "",
  duration_seconds: 0,
  file_size_bytes: 0,
  data_rate_bps: 0,
};

export const useRecordingStore = create<RecordingState>((set) => ({
  ...INITIAL,
  outputDir: "",

  setStatus: (s) => set(s),
  setOutputDir: (dir) => set({ outputDir: dir }),
}));
