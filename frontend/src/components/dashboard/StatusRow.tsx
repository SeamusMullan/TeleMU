/** Status indicator pills — DRS, PIT, FLAG, TC, ABS. */

import type { StatusMessage } from "../../api/types";

interface StatusRowProps {
  status: StatusMessage;
}

const INDICATORS = [
  { key: "drs" as const, label: "DRS", activeColor: "var(--color-green)" },
  { key: "pit" as const, label: "PIT", activeColor: "var(--color-amber)" },
  { key: "tc" as const, label: "TC", activeColor: "var(--color-amber)" },
  { key: "abs" as const, label: "ABS", activeColor: "var(--color-amber)" },
] as const;

export default function StatusRow({ status }: StatusRowProps) {
  const flagActive = status.flag !== 0;
  const flagColor = status.flag === 6 ? "var(--color-blue)" : "var(--color-amber)";

  return (
    <div className="flex gap-2">
      {INDICATORS.map(({ key, label, activeColor }) => {
        const active = status[key];
        return (
          <div
            key={key}
            className="rounded-full px-3 py-1 text-xs font-bold transition-colors"
            style={{
              backgroundColor: active ? activeColor : "#2a2a2a",
              color: active ? "#000" : "#555",
            }}
          >
            {label}
          </div>
        );
      })}
      <div
        className="rounded-full px-3 py-1 text-xs font-bold transition-colors"
        style={{
          backgroundColor: flagActive ? flagColor : "#2a2a2a",
          color: flagActive ? "#000" : "#555",
        }}
      >
        FLAG
      </div>
    </div>
  );
}
