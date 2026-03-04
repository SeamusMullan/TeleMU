import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAlertStore } from "../src/stores/alertStore";

// Reset store state between tests
beforeEach(() => {
  useAlertStore.setState({
    activeAlerts: [],
    history: [],
    flashColor: null,
  });
  // Reset snoozeUntil on all rules
  const rules = useAlertStore.getState().rules.map((r) => ({
    ...r,
    snoozeUntil: 0,
    enabled: true,
  }));
  useAlertStore.setState({ rules });
});

describe("alertStore – rule management", () => {
  it("adds a new rule", () => {
    const before = useAlertStore.getState().rules.length;
    useAlertStore.getState().addRule({
      name: "Test High RPM",
      condition: { type: "above", channel: "rpm", threshold: 8000 },
      notificationTypes: ["banner"],
      sound: "beep",
      enabled: true,
      snoozeUntil: 0,
      profileIds: [],
    });
    expect(useAlertStore.getState().rules.length).toBe(before + 1);
  });

  it("updates a rule", () => {
    const { rules, updateRule } = useAlertStore.getState();
    const ruleId = rules[0].id;
    updateRule(ruleId, { name: "Updated Name" });
    const updated = useAlertStore.getState().rules.find((r) => r.id === ruleId);
    expect(updated?.name).toBe("Updated Name");
  });

  it("deletes a rule", () => {
    useAlertStore.getState().addRule({
      name: "Temp Rule",
      condition: { type: "above", channel: "x", threshold: 1 },
      notificationTypes: [],
      sound: "beep",
      enabled: true,
      snoozeUntil: 0,
      profileIds: [],
    });
    const rules = useAlertStore.getState().rules;
    const last = rules[rules.length - 1];
    useAlertStore.getState().deleteRule(last.id);
    expect(useAlertStore.getState().rules.find((r) => r.id === last.id)).toBeUndefined();
  });
});

describe("alertStore – profile management", () => {
  it("adds a profile", () => {
    const before = useAlertStore.getState().profiles.length;
    useAlertStore.getState().addProfile({ name: "GT3 Car", description: "" });
    expect(useAlertStore.getState().profiles.length).toBe(before + 1);
  });

  it("sets active profile", () => {
    useAlertStore.getState().setActiveProfile("preset");
    expect(useAlertStore.getState().activeProfileId).toBe("preset");
  });

  it("deletes a non-preset profile and resets activeProfileId", () => {
    useAlertStore.getState().addProfile({ name: "My Profile", description: "" });
    const profiles = useAlertStore.getState().profiles;
    const newProfile = profiles[profiles.length - 1];
    useAlertStore.getState().setActiveProfile(newProfile.id);
    useAlertStore.getState().deleteProfile(newProfile.id);
    expect(useAlertStore.getState().activeProfileId).toBeNull();
  });
});

describe("alertStore – alert events", () => {
  it("triggers an alert and adds to activeAlerts and history", () => {
    useAlertStore.getState().triggerAlert({
      ruleId: "r1",
      ruleName: "Test Alert",
      triggeredAt: Date.now(),
      channel: "fuel",
      value: 3,
    });
    const state = useAlertStore.getState();
    expect(state.activeAlerts).toHaveLength(1);
    expect(state.history).toHaveLength(1);
    expect(state.activeAlerts[0].ruleName).toBe("Test Alert");
  });

  it("dismisses an active alert", () => {
    useAlertStore.getState().triggerAlert({
      ruleId: "r1",
      ruleName: "Fuel",
      triggeredAt: Date.now(),
      channel: "fuel",
      value: 3,
    });
    const ev = useAlertStore.getState().activeAlerts[0];
    useAlertStore.getState().dismissAlert(ev.id);
    expect(useAlertStore.getState().activeAlerts).toHaveLength(0);
    const histEv = useAlertStore.getState().history.find((h) => h.id === ev.id);
    expect(histEv?.dismissed).toBe(true);
  });

  it("snooze removes active alerts for rule and sets snoozeUntil", () => {
    const ruleId = useAlertStore.getState().rules[0].id;
    useAlertStore.getState().triggerAlert({
      ruleId,
      ruleName: "Low Fuel",
      triggeredAt: Date.now(),
      channel: "fuel",
      value: 3,
    });
    useAlertStore.getState().snoozeRule(ruleId, 60_000);
    expect(useAlertStore.getState().activeAlerts).toHaveLength(0);
    const rule = useAlertStore.getState().rules.find((r) => r.id === ruleId);
    expect(rule!.snoozeUntil).toBeGreaterThan(Date.now());
  });

  it("clears history", () => {
    useAlertStore.getState().triggerAlert({
      ruleId: "r1",
      ruleName: "Test",
      triggeredAt: Date.now(),
      channel: "x",
      value: 0,
    });
    useAlertStore.getState().clearHistory();
    expect(useAlertStore.getState().history).toHaveLength(0);
  });
});

describe("alertStore – evaluateChannels", () => {
  it("fires a rule when channel exceeds threshold", () => {
    // Add a rule that triggers above 100
    useAlertStore.getState().addRule({
      name: "High Speed",
      condition: { type: "above", channel: "speed", threshold: 100 },
      notificationTypes: [],
      sound: "beep",
      enabled: true,
      snoozeUntil: 0,
      profileIds: ["preset"],
    });

    useAlertStore.getState().evaluateChannels({
      speed: { value: 150, history: [150] },
    });

    expect(useAlertStore.getState().activeAlerts.length).toBeGreaterThan(0);
  });

  it("does not fire for disabled rules", () => {
    useAlertStore.getState().addRule({
      name: "Disabled Rule",
      condition: { type: "above", channel: "speed", threshold: 100 },
      notificationTypes: [],
      sound: "beep",
      enabled: false,
      snoozeUntil: 0,
      profileIds: ["preset"],
    });

    useAlertStore.getState().evaluateChannels({
      speed: { value: 200, history: [200] },
    });

    const newAlerts = useAlertStore
      .getState()
      .activeAlerts.filter((a) => a.ruleName === "Disabled Rule");
    expect(newAlerts).toHaveLength(0);
  });

  it("fires below threshold rule", () => {
    useAlertStore.setState({ activeAlerts: [], history: [] });
    // Use the built-in low-fuel preset
    const fuelRule = useAlertStore
      .getState()
      .rules.find((r) => r.id === "preset-low-fuel")!;
    expect(fuelRule).toBeDefined();

    // Set activeProfileId so the preset rule is in scope
    useAlertStore.setState({ activeProfileId: "preset" });

    useAlertStore.getState().evaluateChannels({
      fuel: { value: 3, history: [3] },
    });

    const alerts = useAlertStore
      .getState()
      .activeAlerts.filter((a) => a.ruleId === "preset-low-fuel");
    expect(alerts.length).toBeGreaterThan(0);
  });
});

describe("alertStore – evaluateStatus", () => {
  it("fires blue flag alert when flag === 6", () => {
    useAlertStore.setState({ activeAlerts: [], history: [] });
    useAlertStore.setState({ activeProfileId: "preset" });

    // Reset cooldown by mocking Date.now to be far in future
    vi.spyOn(Date, "now").mockReturnValue(Date.now() + 100_000);

    useAlertStore.getState().evaluateStatus(false, 6);

    const alerts = useAlertStore
      .getState()
      .activeAlerts.filter((a) => a.ruleId === "preset-blue-flag");
    expect(alerts.length).toBeGreaterThan(0);

    vi.restoreAllMocks();
  });
});
