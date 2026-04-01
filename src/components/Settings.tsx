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
  provider_keys: Record<string, string>;
  provider_limits: Record<string, number>;
}

interface SettingsProps {
  initialConfig: AppConfig;
  onSave: (config: AppConfig) => Promise<void>;
}

interface ProviderDef {
  id: string;
  name: string;
  keyPlaceholder: string;
  hasPublicApi: boolean;
  apiNote?: string;
}

const PROVIDER_DEFS: ProviderDef[] = [
  {
    id: "openai",
    name: "OpenAI",
    keyPlaceholder: "sk-…",
    hasPublicApi: true,
  },
  {
    id: "anthropic",
    name: "Anthropic",
    keyPlaceholder: "sk-ant-…",
    hasPublicApi: false,
    apiNote: "No public usage API yet — key stored for future support.",
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    keyPlaceholder: "sk-…",
    hasPublicApi: true,
  },
  {
    id: "perplexity",
    name: "Perplexity",
    keyPlaceholder: "pplx-…",
    hasPublicApi: false,
    apiNote: "No public usage API yet — key stored for future support.",
  },
  {
    id: "gemini",
    name: "Google Gemini",
    keyPlaceholder: "AIza…",
    hasPublicApi: false,
    apiNote: "No public usage API yet — key stored for future support.",
  },
];

export default function Settings({ initialConfig, onSave }: SettingsProps) {
  const [config, setConfig] = useState<AppConfig>({
    ...initialConfig,
    provider_keys: initialConfig.provider_keys ?? {},
    provider_limits: initialConfig.provider_limits ?? {},
  });
  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({
    github: false,
  });
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

  const toggleShow = (key: string) =>
    setShowTokens((v) => ({ ...v, [key]: !v[key] }));

  const setProviderKey = (id: string, value: string) =>
    setConfig((c) => ({
      ...c,
      provider_keys: { ...c.provider_keys, [id]: value },
    }));

  const setProviderLimit = (id: string, value: string) => {
    const num = parseFloat(value);
    setConfig((c) => ({
      ...c,
      provider_limits: {
        ...c.provider_limits,
        [id]: isNaN(num) ? 0 : num,
      },
    }));
  };

  return (
    <form className="settings" onSubmit={handleSubmit}>
      <h2>Settings</h2>

      {/* ── GitHub ── */}
      <h3 className="settings-section-heading">GitHub</h3>

      <div className="field">
        <label htmlFor="token">GitHub Personal Access Token</label>
        <div className="token-row">
          <input
            id="token"
            type={showTokens.github ? "text" : "password"}
            value={config.token}
            onChange={(e) => setConfig({ ...config, token: e.target.value })}
            placeholder="ghp_…"
            autoComplete="off"
          />
          <button
            type="button"
            className="btn-toggle-token"
            onClick={() => toggleShow("github")}
          >
            {showTokens.github ? "Hide" : "Show"}
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
          {" "}Use organization account
        </label>
      </div>

      {config.use_org && (
        <div className="field">
          <label htmlFor="org-name">Organization Name</label>
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

      {/* ── External AI Providers ── */}
      <h3 className="settings-section-heading">External AI Providers</h3>
      <p className="settings-section-hint">
        Add API keys to enable per-provider token consumption gauges.
        Set a monthly limit to show a spending gauge.
      </p>

      {PROVIDER_DEFS.map((def) => (
        <fieldset key={def.id} className="fieldset fieldset--provider">
          <legend>{def.name}</legend>

          {def.apiNote && (
            <p className="provider-api-note">{def.apiNote}</p>
          )}

          <div className="field">
            <label htmlFor={`key-${def.id}`}>API Key</label>
            <div className="token-row">
              <input
                id={`key-${def.id}`}
                type={showTokens[def.id] ? "text" : "password"}
                value={config.provider_keys[def.id] ?? ""}
                onChange={(e) => setProviderKey(def.id, e.target.value)}
                placeholder={def.keyPlaceholder}
                autoComplete="off"
              />
              <button
                type="button"
                className="btn-toggle-token"
                onClick={() => toggleShow(def.id)}
              >
                {showTokens[def.id] ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {def.hasPublicApi && (
            <div className="field">
              <label htmlFor={`limit-${def.id}`}>
                Monthly Limit (USD, optional)
              </label>
              <input
                id={`limit-${def.id}`}
                type="number"
                min={0}
                step="0.01"
                value={config.provider_limits[def.id] ?? ""}
                onChange={(e) => setProviderLimit(def.id, e.target.value)}
                placeholder="e.g. 50"
              />
              <span className="field-hint">
                Enables the spending gauge bar.
              </span>
            </div>
          )}
        </fieldset>
      ))}

      <button type="submit" className="btn-save" disabled={saving}>
        {saving ? "Saving…" : "Save Settings"}
      </button>
    </form>
  );
}

