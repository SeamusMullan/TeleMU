/** Lap information panel. */

import type { LapInfoMessage } from "../../api/types";

interface LapInfoProps {
  lapInfo: LapInfoMessage | null;
}

export default function LapInfo({ lapInfo }: LapInfoProps) {
  if (!lapInfo) {
    return (
      <div className="rounded-lg bg-neutral-900 p-3">
        <div className="text-xs text-neutral-500">Waiting for lap data...</div>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-neutral-900 p-3">
      <div className="mb-2 text-sm font-bold text-neutral-300">
        Lap {lapInfo.lap}
      </div>
      <div className="space-y-1 font-mono text-sm">
        <div className="flex justify-between">
          <span className="text-neutral-500">Last</span>
          <span className="text-white">{lapInfo.last_time}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-neutral-500">Best</span>
          <span className="text-[var(--color-green)]">{lapInfo.best_time}</span>
        </div>
        {lapInfo.sectors.length > 0 && (
          <div className="mt-2 border-t border-neutral-800 pt-2">
            {lapInfo.sectors.map((s, i) => (
              <div key={i} className="flex justify-between">
                <span className="text-neutral-500">S{i + 1}</span>
                <span className="text-neutral-300">{s}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
