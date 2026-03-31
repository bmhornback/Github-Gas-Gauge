import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import GasGauge from "./components/GasGauge";
import OveragePanel from "./components/OveragePanel";
import BalancePanel from "./components/BalancePanel";
import ProviderGauges, { type ProviderUsage } from "./components/ProviderGauges";
import Settings from "./components/Settings";

interface CopilotUsage {
  used: number;
  quota: number;
  percent_used: number;
  by_model: Record<string, number>;
}

interface ActionsUsage {
  minutes_used: number;
  included_minutes: number;
  paid_minutes_used: number;
  percent_used: number;
  ubuntu_minutes: number;
  macos_minutes: number;
  windows_minutes: number;
}

interface BillingData {
  copilot?: CopilotUsage;
  actions?: ActionsUsage;
  providers: ProviderUsage[];
}

interface AppConfig {
  token: string;
  use_org: boolean;
  org_name: string;
  poll_interval_minutes: number;
  copilot_quota: number;
  alert_75: boolean;
  alert_90: boolean;
  alert_100: boolean;
  provider_keys: Record<string, string>;
  provider_limits: Record<string, number>;
}

type Tab = "dashboard" | "settings";

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [data, setData] = useState<BillingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await invoke<BillingData>("get_billing_data");
      setData(result);
      setLastUpdated(new Date());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadConfig = useCallback(async () => {
    try {
      const cfg = await invoke<AppConfig>("get_config");
      setConfig(cfg);
      if (!cfg.token) {
        setTab("settings");
      }
    } catch (e) {
      console.error("Failed to load config:", e);
    }
  }, []);

  // Schedule next poll
  const schedulePoll = useCallback(() => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
    const intervalMs = (config?.poll_interval_minutes ?? 15) * 60 * 1000;
    pollTimer.current = setTimeout(() => {
      refresh().then(schedulePoll);
    }, intervalMs);
  }, [config?.poll_interval_minutes, refresh]);

  // Initial load
  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  useEffect(() => {
    if (config && config.token) {
      refresh().then(schedulePoll);
    }
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.token]);

  // Listen for background-poll events emitted by Rust
  useEffect(() => {
    const unlisten = listen<BillingData>("billing-updated", (event) => {
      setData(event.payload);
      setLastUpdated(new Date());
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  // Listen for navigation events from tray menu
  useEffect(() => {
    const unlisten = listen("navigate-to-settings", () => {
      setTab("settings");
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const handleSaveConfig = async (newConfig: AppConfig) => {
    await invoke("save_config", { newConfig });
    setConfig(newConfig);
    setTab("dashboard");
    refresh();
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔋 GitHub Gas Gauge</h1>
        <nav className="tabs">
          <button
            className={tab === "dashboard" ? "tab active" : "tab"}
            onClick={() => setTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={tab === "settings" ? "tab active" : "tab"}
            onClick={() => setTab("settings")}
          >
            Settings
          </button>
        </nav>
      </header>

      {tab === "dashboard" && (
        <main className="dashboard">
          <div className="toolbar">
            <button className="btn-refresh" onClick={refresh} disabled={loading}>
              {loading ? "Refreshing…" : "↻ Refresh"}
            </button>
            {lastUpdated && (
              <span className="last-updated">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>

          {error && <div className="error-banner">{error}</div>}

          {!data && !loading && !error && (
            <div className="empty-state">
              <p>No data yet. Click Refresh or configure your token in Settings.</p>
            </div>
          )}

          {data?.copilot && (
            <section className="gauge-section">
              <h2>Copilot Premium Requests</h2>
              <GasGauge
                used={data.copilot.used}
                total={data.copilot.quota}
                label="requests"
              />
              {data.copilot.used > data.copilot.quota && (
                <OveragePanel
                  overageCount={data.copilot.used - data.copilot.quota}
                  unit="requests"
                  costPerUnit={0}
                />
              )}
            </section>
          )}

          {data?.actions && (
            <section className="gauge-section">
              <h2>Actions Minutes</h2>
              <GasGauge
                used={data.actions.minutes_used}
                total={data.actions.included_minutes}
                label="minutes"
              />
              {data.actions.paid_minutes_used > 0 && (
                <OveragePanel
                  overageCount={data.actions.paid_minutes_used}
                  unit="minutes"
                  costPerUnit={0.008}
                />
              )}
            </section>
          )}

          <BalancePanel />
        </main>
      )}

      {tab === "settings" && config && (
        <Settings initialConfig={config} onSave={handleSaveConfig} />
      )}
    </div>
  );
}
