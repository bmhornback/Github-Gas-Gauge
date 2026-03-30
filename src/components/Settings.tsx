import { useState } from "react";

interface AppConfig {
  token: string;
  use_org: boolean;
  org_name: string;
  poll_interval_minutes: number;
  copilot_quota: number;
  alert_75: boolean;
  alert_90: boolean;
  alert_100: boolean;
}

interface SettingsProps {
  initialConfig: AppConfig;
  onSave: (config: AppConfig) => Promise<void>;
}

export default function Settings({ initialConfig, onSave }: SettingsProps) {
  const [config, setConfig] = useState<AppConfig>({ ...initialConfig });
  const [showToken, setShowToken] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(config);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="settings" onSubmit={handleSubmit}>
      <h2>Settings</h2>

      <div className="field">
        <label htmlFor="token">GitHub Personal Access Token</label>
        <div className="token-row">
          <input
            id="token"
            type={showToken ? "text" : "password"}
            value={config.token}
            onChange={(e) => setConfig({ ...config, token: e.target.value })}
            placeholder="ghp_…"
            autoComplete="off"
          />
          <button
            type="button"
            className="btn-toggle-token"
            onClick={() => setShowToken((v) => !v)}
          >
            {showToken ? "Hide" : "Show"}
          </button>
        </div>
        <span className="field-hint">
          Requires <code>copilot</code> scope (personal) or <code>read:org</code> (org).
        </span>
      </div>

      <div className="field field--row">
        <label>
          <input
            type="checkbox"
            checked={config.use_org}
            onChange={(e) => setConfig({ ...config, use_org: e.target.checked })}
          />
          {" "}Use organisation account
        </label>
      </div>

      {config.use_org && (
        <div className="field">
          <label htmlFor="org-name">Organisation Name</label>
          <input
            id="org-name"
            type="text"
            value={config.org_name}
            onChange={(e) => setConfig({ ...config, org_name: e.target.value })}
            placeholder="my-org"
          />
        </div>
      )}

      <div className="field">
        <label htmlFor="poll-interval">Polling Interval</label>
        <select
          id="poll-interval"
          value={config.poll_interval_minutes}
          onChange={(e) =>
            setConfig({ ...config, poll_interval_minutes: Number(e.target.value) })
          }
        >
          <option value={5}>Every 5 minutes</option>
          <option value={15}>Every 15 minutes</option>
          <option value={30}>Every 30 minutes</option>
          <option value={60}>Every hour</option>
        </select>
      </div>

      <div className="field">
        <label htmlFor="copilot-quota">Copilot Monthly Quota</label>
        <input
          id="copilot-quota"
          type="number"
          min={1}
          value={config.copilot_quota}
          onChange={(e) =>
            setConfig({ ...config, copilot_quota: Number(e.target.value) })
          }
        />
      </div>

      <fieldset className="fieldset">
        <legend>Threshold Notifications</legend>
        <label>
          <input
            type="checkbox"
            checked={config.alert_75}
            onChange={(e) => setConfig({ ...config, alert_75: e.target.checked })}
          />
          {" "}Alert at 75%
        </label>
        <label>
          <input
            type="checkbox"
            checked={config.alert_90}
            onChange={(e) => setConfig({ ...config, alert_90: e.target.checked })}
          />
          {" "}Alert at 90%
        </label>
        <label>
          <input
            type="checkbox"
            checked={config.alert_100}
            onChange={(e) => setConfig({ ...config, alert_100: e.target.checked })}
          />
          {" "}Alert at 100%
        </label>
      </fieldset>

      <button type="submit" className="btn-save" disabled={saving}>
        {saving ? "Saving…" : "Save Settings"}
      </button>
    </form>
  );
}
