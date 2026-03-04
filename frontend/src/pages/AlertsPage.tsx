/** Alert management page — rules, profiles, history. */

import { useState, useEffect } from "react";
import {
  useAlertStore,
  type AlertRule,
  type AlertProfile,
  type AlertConditionType,
  type AlertNotificationType,
} from "../stores/alertStore";

const SOUNDS = ["beep", "ping", "klaxon"] as const;
const CONDITION_TYPES: AlertConditionType[] = ["above", "below", "rate_of_change"];
const NOTIFICATION_TYPES: AlertNotificationType[] = ["visual", "sound", "banner"];

// ── Sub-components ─────────────────────────────────────────────────────────

function RuleRow({ rule, profiles, now }: { rule: AlertRule; profiles: AlertProfile[]; now: number }) {
  const { updateRule, deleteRule, snoozeRule } = useAlertStore();
  const [expanded, setExpanded] = useState(false);

  const snoozed = rule.snoozeUntil > now;
  const snoozeRemaining = snoozed
    ? Math.ceil((rule.snoozeUntil - now) / 1000)
    : 0;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900">
      {/* Header row */}
      <div
        className="flex cursor-pointer items-center gap-3 px-4 py-2"
        onClick={() => setExpanded((v) => !v)}
      >
        <input
          type="checkbox"
          checked={rule.enabled}
          onChange={(e) => {
            e.stopPropagation();
            updateRule(rule.id, { enabled: e.target.checked });
          }}
          className="h-4 w-4 accent-[var(--color-accent)]"
        />
        <span className="flex-1 text-sm font-medium">{rule.name}</span>
        <span className="text-xs text-neutral-500">
          {rule.condition.type.replace("_", " ")} {rule.condition.channel}{" "}
          {rule.condition.type !== "rate_of_change" ? rule.condition.threshold : "±" + rule.condition.threshold}
        </span>
        {snoozed && (
          <span className="text-xs text-[var(--color-amber)]">
            snoozed {snoozeRemaining}s
          </span>
        )}
        <div className="flex gap-1">
          {rule.notificationTypes.map((t) => (
            <span
              key={t}
              className="rounded px-1 py-0.5 text-xs"
              style={{ backgroundColor: "#2a2a2a", color: "var(--color-cyan)" }}
            >
              {t}
            </span>
          ))}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            deleteRule(rule.id);
          }}
          className="ml-2 text-xs text-neutral-500 hover:text-[var(--color-red)]"
          aria-label="Delete rule"
        >
          ✕
        </button>
      </div>

      {/* Expanded detail editor */}
      {expanded && (
        <div className="border-t border-neutral-800 px-4 py-3 space-y-3">
          <div className="grid grid-cols-2 gap-3 text-xs text-neutral-300 sm:grid-cols-4">
            {/* Name */}
            <label className="flex flex-col gap-1">
              Name
              <input
                className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
                value={rule.name}
                onChange={(e) => updateRule(rule.id, { name: e.target.value })}
              />
            </label>

            {/* Channel */}
            <label className="flex flex-col gap-1">
              Channel
              <input
                className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
                value={rule.condition.channel}
                onChange={(e) =>
                  updateRule(rule.id, {
                    condition: { ...rule.condition, channel: e.target.value },
                  })
                }
              />
            </label>

            {/* Condition type */}
            <label className="flex flex-col gap-1">
              Condition
              <select
                className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
                value={rule.condition.type}
                onChange={(e) =>
                  updateRule(rule.id, {
                    condition: {
                      ...rule.condition,
                      type: e.target.value as AlertConditionType,
                    },
                  })
                }
              >
                {CONDITION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace("_", " ")}
                  </option>
                ))}
              </select>
            </label>

            {/* Threshold */}
            <label className="flex flex-col gap-1">
              Threshold
              <input
                type="number"
                className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
                value={rule.condition.threshold}
                onChange={(e) =>
                  updateRule(rule.id, {
                    condition: {
                      ...rule.condition,
                      threshold: Number(e.target.value),
                    },
                  })
                }
              />
            </label>
          </div>

          {/* Notification types */}
          <div className="flex flex-wrap gap-3 text-xs text-neutral-300">
            <span className="mt-0.5">Notify via:</span>
            {NOTIFICATION_TYPES.map((t) => (
              <label key={t} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={rule.notificationTypes.includes(t)}
                  onChange={(e) => {
                    const types = e.target.checked
                      ? [...rule.notificationTypes, t]
                      : rule.notificationTypes.filter((x) => x !== t);
                    updateRule(rule.id, { notificationTypes: types });
                  }}
                  className="accent-[var(--color-accent)]"
                />
                {t}
              </label>
            ))}
          </div>

          {/* Sound */}
          <div className="flex items-center gap-3 text-xs text-neutral-300">
            <span>Sound:</span>
            <select
              className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
              value={rule.sound}
              onChange={(e) => updateRule(rule.id, { sound: e.target.value })}
            >
              {SOUNDS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Profile membership */}
          <div className="flex flex-wrap gap-3 text-xs text-neutral-300">
            <span className="mt-0.5">Profiles:</span>
            {profiles.map((p) => (
              <label key={p.id} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={rule.profileIds.includes(p.id)}
                  onChange={(e) => {
                    const ids = e.target.checked
                      ? [...rule.profileIds, p.id]
                      : rule.profileIds.filter((x) => x !== p.id);
                    updateRule(rule.id, { profileIds: ids });
                  }}
                  className="accent-[var(--color-accent)]"
                />
                {p.name}
              </label>
            ))}
          </div>

          {/* Snooze / unsnooze */}
          {snoozed ? (
            <button
              onClick={() => snoozeRule(rule.id, 0)}
              className="text-xs text-[var(--color-amber)] hover:underline"
            >
              Cancel snooze
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

// ── New Rule Form ──────────────────────────────────────────────────────────

const EMPTY_RULE: Omit<AlertRule, "id"> = {
  name: "",
  condition: { type: "above", channel: "", threshold: 0 },
  notificationTypes: ["banner"],
  sound: "beep",
  enabled: true,
  snoozeUntil: 0,
  profileIds: [],
};

function NewRuleForm({ profiles, onDone }: { profiles: AlertProfile[]; onDone: () => void }) {
  const addRule = useAlertStore((s) => s.addRule);
  const [draft, setDraft] = useState<Omit<AlertRule, "id">>(EMPTY_RULE);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.name || !draft.condition.channel) return;
    addRule(draft);
    onDone();
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-neutral-700 bg-neutral-900 p-4 space-y-3">
      <h3 className="text-sm font-bold text-neutral-200">New Alert Rule</h3>

      <div className="grid grid-cols-2 gap-3 text-xs text-neutral-300 sm:grid-cols-4">
        <label className="flex flex-col gap-1">
          Name *
          <input
            required
            className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
            value={draft.name}
            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1">
          Channel *
          <input
            required
            placeholder="e.g. fuel"
            className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
            value={draft.condition.channel}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                condition: { ...d.condition, channel: e.target.value },
              }))
            }
          />
        </label>
        <label className="flex flex-col gap-1">
          Condition
          <select
            className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
            value={draft.condition.type}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                condition: {
                  ...d.condition,
                  type: e.target.value as AlertConditionType,
                },
              }))
            }
          >
            {CONDITION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Threshold
          <input
            type="number"
            className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
            value={draft.condition.threshold}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                condition: { ...d.condition, threshold: Number(e.target.value) },
              }))
            }
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-neutral-300">
        <span className="mt-0.5">Notify via:</span>
        {NOTIFICATION_TYPES.map((t) => (
          <label key={t} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={draft.notificationTypes.includes(t)}
              onChange={(e) => {
                const types = e.target.checked
                  ? [...draft.notificationTypes, t]
                  : draft.notificationTypes.filter((x) => x !== t);
                setDraft((d) => ({ ...d, notificationTypes: types }));
              }}
              className="accent-[var(--color-accent)]"
            />
            {t}
          </label>
        ))}
        <label className="flex items-center gap-3 ml-4">
          Sound:
          <select
            className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
            value={draft.sound}
            onChange={(e) => setDraft((d) => ({ ...d, sound: e.target.value }))}
          >
            {SOUNDS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-neutral-300">
        <span className="mt-0.5">Profiles:</span>
        {profiles.map((p) => (
          <label key={p.id} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={draft.profileIds.includes(p.id)}
              onChange={(e) => {
                const ids = e.target.checked
                  ? [...draft.profileIds, p.id]
                  : draft.profileIds.filter((x) => x !== p.id);
                setDraft((d) => ({ ...d, profileIds: ids }));
              }}
              className="accent-[var(--color-accent)]"
            />
            {p.name}
          </label>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          className="rounded px-3 py-1.5 text-xs font-bold text-white transition-opacity hover:opacity-80"
          style={{ backgroundColor: "var(--color-accent)" }}
        >
          Add Rule
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded px-3 py-1.5 text-xs text-neutral-400 hover:text-neutral-200"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const {
    rules,
    profiles,
    activeProfileId,
    setActiveProfile,
    addProfile,
    deleteProfile,
    activeAlerts,
    history,
    dismissAlert,
    clearHistory,
  } = useAlertStore();

  const [tab, setTab] = useState<"rules" | "profiles" | "history">("rules");
  const [showNewRule, setShowNewRule] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [now, setNow] = useState(() => Date.now());

  // Refresh `now` every second so snooze countdowns stay accurate
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const filteredRules =
    activeProfileId === null
      ? rules
      : rules.filter(
          (r) =>
            r.profileIds.includes(activeProfileId) ||
            r.profileIds.includes("preset"),
        );

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Alerts &amp; Notifications</h1>

        {/* Active profile selector */}
        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <span>Profile:</span>
          <select
            className="rounded bg-neutral-800 px-2 py-1 text-white outline-none"
            value={activeProfileId ?? ""}
            onChange={(e) =>
              setActiveProfile(e.target.value === "" ? null : e.target.value)
            }
          >
            <option value="">All</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Active alerts summary */}
      {activeAlerts.length > 0 && (
        <div className="rounded-lg border border-[var(--color-red)] bg-neutral-900 p-3">
          <div className="mb-2 text-xs font-bold text-[var(--color-red)]">
            Active Alerts ({activeAlerts.length})
          </div>
          <div className="space-y-1">
            {activeAlerts.map((ev) => (
              <div key={ev.id} className="flex items-center justify-between text-xs">
                <span className="text-neutral-200">
                  {ev.ruleName}{" "}
                  <span className="text-neutral-500">
                    — {ev.channel}: {ev.value.toFixed(1)}
                  </span>
                </span>
                <button
                  onClick={() => dismissAlert(ev.id)}
                  className="text-neutral-500 hover:text-[var(--color-red)]"
                  aria-label="Dismiss"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-neutral-800">
        {(["rules", "profiles", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-sm capitalize transition-colors ${
              tab === t
                ? "border-b-2 border-[var(--color-accent)] text-white"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── Rules tab ────────────────────────────────────── */}
      {tab === "rules" && (
        <div className="space-y-2">
          {filteredRules.map((rule) => (
            <RuleRow key={rule.id} rule={rule} profiles={profiles} now={now} />
          ))}

          {!showNewRule ? (
            <button
              onClick={() => setShowNewRule(true)}
              className="mt-2 rounded px-3 py-1.5 text-xs font-bold text-white transition-opacity hover:opacity-80"
              style={{ backgroundColor: "var(--color-accent)" }}
            >
              + Add Rule
            </button>
          ) : (
            <NewRuleForm
              profiles={profiles}
              onDone={() => setShowNewRule(false)}
            />
          )}
        </div>
      )}

      {/* ── Profiles tab ─────────────────────────────────── */}
      {tab === "profiles" && (
        <div className="space-y-3">
          {profiles.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-2"
            >
              <div>
                <div className="text-sm font-medium">{p.name}</div>
                {p.description && (
                  <div className="text-xs text-neutral-500">{p.description}</div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveProfile(p.id)}
                  className={`rounded px-2 py-0.5 text-xs transition-colors ${
                    activeProfileId === p.id
                      ? "font-bold text-[var(--color-green)]"
                      : "text-neutral-400 hover:text-neutral-200"
                  }`}
                >
                  {activeProfileId === p.id ? "Active" : "Activate"}
                </button>
                {p.id !== "preset" && (
                  <button
                    onClick={() => deleteProfile(p.id)}
                    className="text-xs text-neutral-500 hover:text-[var(--color-red)]"
                    aria-label="Delete profile"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          ))}

          {/* Add profile */}
          <div className="flex gap-2">
            <input
              className="rounded bg-neutral-800 px-3 py-1.5 text-sm text-white outline-none"
              placeholder="New profile name"
              value={newProfileName}
              onChange={(e) => setNewProfileName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newProfileName.trim()) {
                  addProfile({
                    name: newProfileName.trim(),
                    description: "",
                  });
                  setNewProfileName("");
                }
              }}
            />
            <button
              onClick={() => {
                if (!newProfileName.trim()) return;
                addProfile({ name: newProfileName.trim(), description: "" });
                setNewProfileName("");
              }}
              className="rounded px-3 py-1.5 text-xs font-bold text-white transition-opacity hover:opacity-80"
              style={{ backgroundColor: "var(--color-accent)" }}
            >
              Add Profile
            </button>
          </div>
        </div>
      )}

      {/* ── History tab ──────────────────────────────────── */}
      {tab === "history" && (
        <div className="space-y-2">
          <div className="flex justify-end">
            <button
              onClick={clearHistory}
              className="text-xs text-neutral-500 hover:text-[var(--color-red)]"
            >
              Clear History
            </button>
          </div>

          {history.length === 0 ? (
            <div className="text-sm text-neutral-500">No alert history yet.</div>
          ) : (
            <div className="overflow-auto rounded-lg border border-neutral-800">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-neutral-800 bg-neutral-900 text-neutral-400">
                    <th className="px-3 py-2 text-left">Time</th>
                    <th className="px-3 py-2 text-left">Rule</th>
                    <th className="px-3 py-2 text-left">Channel</th>
                    <th className="px-3 py-2 text-left">Value</th>
                    <th className="px-3 py-2 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((ev) => (
                    <tr
                      key={ev.id}
                      className="border-b border-neutral-800 text-neutral-300 last:border-0"
                    >
                      <td className="px-3 py-1.5 font-mono">
                        {new Date(ev.triggeredAt).toLocaleTimeString()}
                      </td>
                      <td className="px-3 py-1.5">{ev.ruleName}</td>
                      <td className="px-3 py-1.5 font-mono text-neutral-500">
                        {ev.channel}
                      </td>
                      <td className="px-3 py-1.5 font-mono">{ev.value.toFixed(2)}</td>
                      <td className="px-3 py-1.5">
                        {ev.dismissed ? (
                          <span className="text-neutral-600">dismissed</span>
                        ) : (
                          <span className="text-[var(--color-amber)]">active</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
