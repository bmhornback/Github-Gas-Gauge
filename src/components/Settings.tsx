import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { AppConfig } from "../App";

interface SettingsProps {
  initialConfig: AppConfig | null;
  onSaved: () => void;
  onCancel: () => void;
}

const DEFAULT_CONFIG: AppConfig = {
  github_pat: null,
  use_org: false,
  org_name: null,
  polling_interval: "fifteen_minutes",
  alert_thresholds: {
    notify_at_75: true,
    notify_at_90: true,
    notify_at_100: true,
  },
};

function Settings({ initialConfig, onSaved, onCancel }: SettingsProps) {
  const [pat, setPat] = useState("");
  const [showPat, setShowPat] = useState(false);
  const [useOrg, setUseOrg] = useState(false);
  const [orgName, setOrgName] = useState("");
  const [pollingInterval, setPollingInterval] =
    useState<AppConfig["polling_interval"]>("fifteen_minutes");
  const [notify75, setNotify75] = useState(true);
  const [notify90, setNotify90] = useState(true);
  const [notify100, setNotify100] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    const cfg = initialConfig ?? DEFAULT_CONFIG;
    setPat(cfg.github_pat ?? "");
    setUseOrg(cfg.use_org);
    setOrgName(cfg.org_name ?? "");
    setPollingInterval(cfg.polling_interval);
    setNotify75(cfg.alert_thresholds.notify_at_75);
    setNotify90(cfg.alert_thresholds.notify_at_90);
    setNotify100(cfg.alert_thresholds.notify_at_100);
  }, [initialConfig]);

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const config: AppConfig = {
      github_pat: pat.trim() || null,
      use_org: useOrg,
      org_name: orgName.trim() || null,
      polling_interval: pollingInterval,
      alert_thresholds: {
        notify_at_75: notify75,
        notify_at_90: notify90,
        notify_at_100: notify100,
      },
    };

    try {
      await invoke("save_config_cmd", { newConfig: config });
      setSaveSuccess(true);
      setTimeout(() => {
        onSaved();
      }, 800);
    } catch (e) {
      setSaveError(typeof e === "string" ? e : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="settings-panel">
      <h2 className="settings-title">⚙️ Settings</h2>

      {/* GitHub PAT */}
      <div className="form-group">
        <label className="form-label" htmlFor="pat-input">
          GitHub Personal Access Token
        </label>
        <div className="input-row">
          <input
            id="pat-input"
            type={showPat ? "text" : "password"}
            className="form-input"
            value={pat}
            onChange={(e) => setPat(e.target.value)}
            placeholder="ghp_…"
            autoComplete="off"
          />
          <button
            type="button"
            className="btn-icon"
            onClick={() => setShowPat((s) => !s)}
            title={showPat ? "Hide token" : "Show token"}
          >
            {showPat ? "🙈" : "👁️"}
          </button>
        </div>
        <p className="form-hint">
          Requires <code>read:org</code> scope for org accounts, or{" "}
          <code>user</code> scope for personal.{" "}
          <a
            href="https://github.com/settings/tokens/new"
            target="_blank"
            rel="noopener noreferrer"
          >
            Create a token ↗
          </a>
        </p>
      </div>

      {/* Account mode */}
      <div className="form-group">
        <label className="form-label">Account Type</label>
        <div className="toggle-row">
          <label className="toggle-option">
            <input
              type="radio"
              name="account-type"
              checked={!useOrg}
              onChange={() => setUseOrg(false)}
            />
            Personal Account
          </label>
          <label className="toggle-option">
            <input
              type="radio"
              name="account-type"
              checked={useOrg}
              onChange={() => setUseOrg(true)}
            />
            Organization
          </label>
        </div>
        {useOrg && (
          <input
            type="text"
            className="form-input"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            placeholder="my-org-name"
            style={{ marginTop: "0.5rem" }}
          />
        )}
      </div>

      {/* Polling interval */}
      <div className="form-group">
        <label className="form-label" htmlFor="polling-select">
          Polling Interval
        </label>
        <select
          id="polling-select"
          className="form-input"
          value={pollingInterval}
          onChange={(e) =>
            setPollingInterval(e.target.value as AppConfig["polling_interval"])
          }
        >
          <option value="five_minutes">Every 5 minutes</option>
          <option value="fifteen_minutes">Every 15 minutes</option>
          <option value="thirty_minutes">Every 30 minutes</option>
          <option value="one_hour">Every hour</option>
        </select>
      </div>

      {/* Threshold notifications */}
      <div className="form-group">
        <label className="form-label">Threshold Notifications</label>
        <div className="checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={notify75}
              onChange={(e) => setNotify75(e.target.checked)}
            />
            🟡 Notify at 75%
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={notify90}
              onChange={(e) => setNotify90(e.target.checked)}
            />
            🟠 Notify at 90%
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={notify100}
              onChange={(e) => setNotify100(e.target.checked)}
            />
            🔴 Notify at 100%
          </label>
        </div>
      </div>

      {/* Feedback */}
      {saveError && <div className="error-banner">⚠️ {saveError}</div>}
      {saveSuccess && (
        <div className="success-banner">✅ Settings saved! Refreshing…</div>
      )}

      {/* Actions */}
      <div className="action-row">
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving…" : "Save Settings"}
        </button>
        {initialConfig?.github_pat && (
          <button className="btn-secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

export default Settings;
