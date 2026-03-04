/** Persistent alert banner shown at the bottom of the screen. */

import { useAlertStore } from "../../stores/alertStore";

const SNOOZE_OPTIONS = [
  { label: "30 s", ms: 30_000 },
  { label: "2 min", ms: 120_000 },
  { label: "5 min", ms: 300_000 },
];

export default function AlertBanner() {
  const activeAlerts = useAlertStore((s) => s.activeAlerts);
  const dismissAlert = useAlertStore((s) => s.dismissAlert);
  const snoozeRule = useAlertStore((s) => s.snoozeRule);

  const bannerAlerts = activeAlerts.filter((e) => {
    const rule = useAlertStore
      .getState()
      .rules.find((r) => r.id === e.ruleId);
    return rule?.notificationTypes.includes("banner") ?? true;
  });

  if (bannerAlerts.length === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 flex flex-col gap-1 p-2">
      {bannerAlerts.map((ev) => (
        <div
          key={ev.id}
          className="flex items-center justify-between rounded-lg px-4 py-2 text-sm font-medium shadow-lg"
          style={{ backgroundColor: "var(--color-red)", color: "#fff" }}
        >
          <span>
            ⚠ {ev.ruleName}{" "}
            <span className="opacity-75">
              ({ev.channel}: {ev.value.toFixed(1)})
            </span>
          </span>

          <div className="flex items-center gap-2">
            {/* Snooze buttons */}
            {SNOOZE_OPTIONS.map((opt) => (
              <button
                key={opt.label}
                onClick={() => snoozeRule(ev.ruleId, opt.ms)}
                className="rounded px-2 py-0.5 text-xs transition-opacity hover:opacity-80"
                style={{ backgroundColor: "rgba(0,0,0,0.3)" }}
              >
                Snooze {opt.label}
              </button>
            ))}
            {/* Dismiss */}
            <button
              onClick={() => dismissAlert(ev.id)}
              className="rounded px-2 py-0.5 text-xs font-bold transition-opacity hover:opacity-80"
              style={{ backgroundColor: "rgba(0,0,0,0.4)" }}
              aria-label="Dismiss alert"
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
