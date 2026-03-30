import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import GasGauge from "./components/GasGauge";
import OveragePanel from "./components/OveragePanel";
import BalancePanel from "./components/BalancePanel";
import Settings from "./components/Settings";

export interface BillingData {
  total_minutes_used: number;
  total_paid_minutes_used: number;
  included_minutes: number;
  minutes_used_breakdown: {
    ubuntu: number;
    macos: number;
    windows: number;
  };
}

export interface AppConfig {
  github_pat: string | null;
  use_org: boolean;
  org_name: string | null;
  polling_interval:
    | "five_minutes"
    | "fifteen_minutes"
    | "thirty_minutes"
    | "one_hour";
  alert_thresholds: {
    notify_at_75: boolean;
    notify_at_90: boolean;
    notify_at_100: boolean;
  };
}

const POLLING_MINUTES: Record<AppConfig["polling_interval"], number> = {
  five_minutes: 5,
  fifteen_minutes: 15,
  thirty_minutes: 30,
  one_hour: 60,
};

type Tab = "dashboard" | "settings";

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [billing, setBilling] = useState<BillingData | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchBilling = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await invoke<BillingData>("get_billing_data");
      setBilling(data);
      setLastUpdated(new Date());
    } catch (e) {
      setError(typeof e === "string" ? e : "Failed to fetch billing data.");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const cfg = await invoke<AppConfig>("get_config");
      setConfig(cfg);
      return cfg;
    } catch {
      return null;
    }
  }, []);

  const startPolling = useCallback(
    (cfg: AppConfig) => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      const intervalMs = POLLING_MINUTES[cfg.polling_interval] * 60 * 1000;
      pollingRef.current = setInterval(fetchBilling, intervalMs);
    },
    [fetchBilling]
  );

  useEffect(() => {
    (async () => {
      const cfg = await fetchConfig();
      if (!cfg?.github_pat) {
        setActiveTab("settings");
        return;
      }
      await fetchBilling();
      startPolling(cfg);
    })();

    // Listen for tray "Refresh Now" events.
    const unlisten = listen("refresh-requested", () => fetchBilling());

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      unlisten.then((fn) => fn());
    };
  }, [fetchBilling, fetchConfig, startPolling]);

  const handleConfigSaved = useCallback(async () => {
    const cfg = await fetchConfig();
    if (cfg) startPolling(cfg);
    await fetchBilling();
    setActiveTab("dashboard");
  }, [fetchConfig, fetchBilling, startPolling]);

  const usagePct =
    billing && billing.included_minutes > 0
      ? (billing.total_minutes_used / billing.included_minutes) * 100
      : 0;

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-brand">
          <span className="app-logo">⛽</span>
          <div>
            <h1 className="app-title">GitHub Gas Gauge</h1>
            <p className="app-subtitle">A HornToad Labs Open Source Project</p>
          </div>
        </div>
        <nav className="app-nav">
          <button
            className={`nav-btn ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`nav-btn ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            Settings
          </button>
        </nav>
      </header>

      <main className="app-main">
        {activeTab === "dashboard" && (
          <div className="dashboard">
            {error && (
              <div className="error-banner">
                <span>⚠️ {error}</span>
                <button
                  onClick={() => setActiveTab("settings")}
                  className="btn-link"
                >
                  Open Settings
                </button>
              </div>
            )}

            <div className="gauge-section">
              <GasGauge percentage={usagePct} loading={loading} />
              {billing && (
                <p className="minutes-label">
                  {billing.total_minutes_used.toFixed(0)} minutes used of{" "}
                  {billing.included_minutes.toFixed(0)} included
                </p>
              )}
            </div>

            {billing && billing.total_paid_minutes_used > 0 && (
              <OveragePanel
                paidMinutes={billing.total_paid_minutes_used}
                breakdown={billing.minutes_used_breakdown}
              />
            )}

            <BalancePanel billing={billing} />

            <div className="action-row">
              <button
                className="btn-primary"
                onClick={fetchBilling}
                disabled={loading}
              >
                {loading ? "Refreshing…" : "Refresh Now"}
              </button>
              {lastUpdated && (
                <span className="last-updated">
                  Last updated: {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <Settings
            initialConfig={config}
            onSaved={handleConfigSaved}
            onCancel={() => setActiveTab("dashboard")}
          />
        )}
      </main>

      <footer className="app-footer">
        <span>GitHub Gas Gauge · HornToad Labs · MIT License</span>
      </footer>
    </div>
  );
}

export default App;
