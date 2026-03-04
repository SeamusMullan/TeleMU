/** Alert and notification state — rules, profiles, active alerts, history. */

import { create } from "zustand";
import { persist } from "zustand/middleware";

// ── Types ──────────────────────────────────────────────────────────────────

export type AlertConditionType = "above" | "below" | "rate_of_change";
export type AlertNotificationType = "visual" | "sound" | "banner";

export interface AlertCondition {
  type: AlertConditionType;
  /** telemetry channel name, e.g. "fuel", "tyre_fl" */
  channel: string;
  threshold: number;
  /** used only for rate_of_change: how many history samples to look back */
  window?: number;
}

export interface AlertRule {
  id: string;
  name: string;
  condition: AlertCondition;
  notificationTypes: AlertNotificationType[];
  /** Sound id to use, e.g. "beep", "klaxon", "ping" */
  sound: string;
  enabled: boolean;
  /** Unix ms – if set and < Date.now(), rule is effectively snoozed */
  snoozeUntil: number;
  /** Profile IDs this rule belongs to */
  profileIds: string[];
}

export interface AlertProfile {
  id: string;
  name: string;
  description: string;
}

export interface AlertEvent {
  id: string;
  ruleId: string;
  ruleName: string;
  triggeredAt: number;
  channel: string;
  value: number;
  dismissed: boolean;
}

interface AlertState {
  rules: AlertRule[];
  profiles: AlertProfile[];
  activeProfileId: string | null;
  activeAlerts: AlertEvent[];
  history: AlertEvent[];
  /** Flash overlay: set to a color string for ~800 ms on visual alert */
  flashColor: string | null;

  addRule: (rule: Omit<AlertRule, "id">) => void;
  updateRule: (id: string, updates: Partial<Omit<AlertRule, "id">>) => void;
  deleteRule: (id: string) => void;

  addProfile: (profile: Omit<AlertProfile, "id">) => void;
  updateProfile: (id: string, updates: Partial<Omit<AlertProfile, "id">>) => void;
  deleteProfile: (id: string) => void;
  setActiveProfile: (id: string | null) => void;

  triggerAlert: (event: Omit<AlertEvent, "id" | "dismissed">) => void;
  dismissAlert: (eventId: string) => void;
  snoozeRule: (ruleId: string, durationMs: number) => void;
  clearHistory: () => void;
  setFlashColor: (color: string | null) => void;

  evaluateChannels: (channels: Record<string, { value: number; history: number[] }>) => void;
  evaluateStatus: (drs: boolean, flag: number) => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

function ruleIsActive(rule: AlertRule): boolean {
  return rule.enabled && Date.now() >= rule.snoozeUntil;
}

function checkCondition(
  rule: AlertRule,
  channels: Record<string, { value: number; history: number[] }>,
): boolean {
  const ch = channels[rule.condition.channel];
  if (!ch) return false;
  const { type, threshold, window: win = 5 } = rule.condition;
  if (type === "above") return ch.value > threshold;
  if (type === "below") return ch.value < threshold;
  if (type === "rate_of_change") {
    const hist = ch.history;
    if (hist.length < 2) return false;
    const slice = hist.slice(-win);
    const rate = (slice[slice.length - 1]! - slice[0]!) / slice.length;
    return Math.abs(rate) > threshold;
  }
  return false;
}

// ── Built-in presets ───────────────────────────────────────────────────────

const PRESET_PROFILE: AlertProfile = {
  id: "preset",
  name: "Built-in Presets",
  description: "Default presets for common racing alerts",
};

const PRESET_RULES: AlertRule[] = [
  {
    id: "preset-low-fuel",
    name: "Low Fuel",
    condition: { type: "below", channel: "fuel", threshold: 5 },
    notificationTypes: ["visual", "sound", "banner"],
    sound: "klaxon",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
  {
    id: "preset-high-tyre-fl",
    name: "High Tyre Temp (FL)",
    condition: { type: "above", channel: "tyre_fl", threshold: 115 },
    notificationTypes: ["visual", "banner"],
    sound: "beep",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
  {
    id: "preset-high-tyre-fr",
    name: "High Tyre Temp (FR)",
    condition: { type: "above", channel: "tyre_fr", threshold: 115 },
    notificationTypes: ["visual", "banner"],
    sound: "beep",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
  {
    id: "preset-high-tyre-rl",
    name: "High Tyre Temp (RL)",
    condition: { type: "above", channel: "tyre_rl", threshold: 115 },
    notificationTypes: ["visual", "banner"],
    sound: "beep",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
  {
    id: "preset-high-tyre-rr",
    name: "High Tyre Temp (RR)",
    condition: { type: "above", channel: "tyre_rr", threshold: 115 },
    notificationTypes: ["visual", "banner"],
    sound: "beep",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
  {
    id: "preset-blue-flag",
    name: "Blue Flag",
    condition: { type: "above", channel: "__flag__", threshold: 5 },
    notificationTypes: ["visual", "sound", "banner"],
    sound: "ping",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
  {
    id: "preset-drs",
    name: "DRS Available",
    condition: { type: "above", channel: "__drs__", threshold: 0 },
    notificationTypes: ["banner"],
    sound: "ping",
    enabled: true,
    snoozeUntil: 0,
    profileIds: ["preset"],
  },
];

// ── Alert sound helper (Web Audio API) ────────────────────────────────────

let audioCtx: AudioContext | null = null;

function getAudioCtx(): AudioContext {
  if (!audioCtx) audioCtx = new AudioContext();
  return audioCtx;
}

export function playAlertSound(sound: string): void {
  try {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (sound === "klaxon") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.setValueAtTime(380, ctx.currentTime + 0.15);
      osc.frequency.setValueAtTime(440, ctx.currentTime + 0.3);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.5);
    } else if (sound === "ping") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      gain.gain.setValueAtTime(0.25, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
    } else {
      // default "beep"
      osc.type = "square";
      osc.frequency.setValueAtTime(660, ctx.currentTime);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.2);
    }
  } catch {
    // AudioContext unavailable in test or headless env – silent fail
  }
}

// ── Store ──────────────────────────────────────────────────────────────────

/** Cooldown map: ruleId → last trigger timestamp (to avoid spam) */
const triggerCooldown: Record<string, number> = {};
const COOLDOWN_MS = 5000;

export const useAlertStore = create<AlertState>()(
  persist(
    (set, get) => ({
      rules: PRESET_RULES,
      profiles: [PRESET_PROFILE],
      activeProfileId: "preset",
      activeAlerts: [],
      history: [],
      flashColor: null,

      addRule: (rule) =>
        set((s) => ({ rules: [...s.rules, { ...rule, id: uid() }] })),

      updateRule: (id, updates) =>
        set((s) => ({
          rules: s.rules.map((r) => (r.id === id ? { ...r, ...updates } : r)),
        })),

      deleteRule: (id) =>
        set((s) => ({ rules: s.rules.filter((r) => r.id !== id) })),

      addProfile: (profile) =>
        set((s) => ({ profiles: [...s.profiles, { ...profile, id: uid() }] })),

      updateProfile: (id, updates) =>
        set((s) => ({
          profiles: s.profiles.map((p) =>
            p.id === id ? { ...p, ...updates } : p,
          ),
        })),

      deleteProfile: (id) =>
        set((s) => ({
          profiles: s.profiles.filter((p) => p.id !== id),
          activeProfileId:
            s.activeProfileId === id ? null : s.activeProfileId,
        })),

      setActiveProfile: (id) => set({ activeProfileId: id }),

      triggerAlert: (event) => {
        const ev: AlertEvent = { ...event, id: uid(), dismissed: false };
        set((s) => ({
          activeAlerts: [...s.activeAlerts, ev],
          history: [ev, ...s.history].slice(0, 200),
        }));
      },

      dismissAlert: (eventId) =>
        set((s) => ({
          activeAlerts: s.activeAlerts.filter((e) => e.id !== eventId),
          history: s.history.map((e) =>
            e.id === eventId ? { ...e, dismissed: true } : e,
          ),
        })),

      snoozeRule: (ruleId, durationMs) =>
        set((s) => ({
          rules: s.rules.map((r) =>
            r.id === ruleId
              ? { ...r, snoozeUntil: Date.now() + durationMs }
              : r,
          ),
          activeAlerts: s.activeAlerts.filter((e) => e.ruleId !== ruleId),
        })),

      clearHistory: () => set({ history: [] }),

      setFlashColor: (color) => set({ flashColor: color }),

      evaluateChannels: (channels) => {
        const state = get();
        const now = Date.now();

        for (const rule of state.rules) {
          if (!ruleIsActive(rule)) continue;
          // Profile filter
          if (
            state.activeProfileId &&
            !rule.profileIds.includes(state.activeProfileId) &&
            !rule.profileIds.includes("preset")
          )
            continue;
          // Skip virtual-channel rules here (handled in evaluateStatus)
          if (
            rule.condition.channel === "__flag__" ||
            rule.condition.channel === "__drs__"
          )
            continue;

          if (checkCondition(rule, channels)) {
            const last = triggerCooldown[rule.id] ?? 0;
            if (now - last < COOLDOWN_MS) continue;
            triggerCooldown[rule.id] = now;

            const ch = channels[rule.condition.channel]!;
            state.triggerAlert({
              ruleId: rule.id,
              ruleName: rule.name,
              triggeredAt: now,
              channel: rule.condition.channel,
              value: ch.value,
            });

            if (rule.notificationTypes.includes("sound")) {
              playAlertSound(rule.sound);
            }
            if (rule.notificationTypes.includes("visual")) {
              get().setFlashColor("var(--color-red)");
              setTimeout(() => get().setFlashColor(null), 800);
            }
          }
        }
      },

      evaluateStatus: (drs, flag) => {
        const state = get();
        const now = Date.now();

        // Build synthetic channel map for virtual channels
        const virtualChannels: Record<string, { value: number; history: number[] }> = {
          __drs__: { value: drs ? 1 : 0, history: [drs ? 1 : 0] },
          __flag__: { value: flag, history: [flag] },
        };

        for (const rule of state.rules) {
          if (!ruleIsActive(rule)) continue;
          if (
            rule.condition.channel !== "__flag__" &&
            rule.condition.channel !== "__drs__"
          )
            continue;

          if (checkCondition(rule, virtualChannels)) {
            const last = triggerCooldown[rule.id] ?? 0;
            if (now - last < COOLDOWN_MS) continue;
            triggerCooldown[rule.id] = now;

            const ch = virtualChannels[rule.condition.channel]!;
            state.triggerAlert({
              ruleId: rule.id,
              ruleName: rule.name,
              triggeredAt: now,
              channel: rule.condition.channel,
              value: ch.value,
            });

            if (rule.notificationTypes.includes("sound")) {
              playAlertSound(rule.sound);
            }
            if (rule.notificationTypes.includes("visual")) {
              get().setFlashColor(
                rule.condition.channel === "__flag__"
                  ? "var(--color-blue)"
                  : "var(--color-green)",
              );
              setTimeout(() => get().setFlashColor(null), 800);
            }
          }
        }
      },
    }),
    {
      name: "telemu-alerts",
      // Only persist rules, profiles and history; don't persist transient alert state
      partialize: (s) => ({
        rules: s.rules,
        profiles: s.profiles,
        activeProfileId: s.activeProfileId,
        history: s.history,
      }),
    },
  ),
);
