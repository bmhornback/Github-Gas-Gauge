use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

/// Polling interval options (in minutes).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum PollingInterval {
    FiveMinutes,
    FifteenMinutes,
    ThirtyMinutes,
    OneHour,
}

impl PollingInterval {
    pub fn as_minutes(&self) -> u64 {
        match self {
            PollingInterval::FiveMinutes => 5,
            PollingInterval::FifteenMinutes => 15,
            PollingInterval::ThirtyMinutes => 30,
            PollingInterval::OneHour => 60,
        }
    }
}

impl Default for PollingInterval {
    fn default() -> Self {
        PollingInterval::FifteenMinutes
    }
}

/// Alert threshold configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertThresholds {
    pub notify_at_75: bool,
    pub notify_at_90: bool,
    pub notify_at_100: bool,
}

impl Default for AlertThresholds {
    fn default() -> Self {
        Self {
            notify_at_75: true,
            notify_at_90: true,
            notify_at_100: true,
        }
    }
}

/// Full app configuration stored on disk.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppConfig {
    /// GitHub Personal Access Token (stored in plain text in local config).
    pub github_pat: Option<String>,
    /// Whether to monitor an org (true) or personal account (false).
    pub use_org: bool,
    /// Organization name (used when use_org is true).
    pub org_name: Option<String>,
    /// How often to poll the GitHub API.
    pub polling_interval: PollingInterval,
    /// Which thresholds fire notifications.
    pub alert_thresholds: AlertThresholds,
}

/// Return the path to the config file in the app data directory.
pub fn config_path() -> PathBuf {
    let base = dirs::data_local_dir()
        .or_else(|| dirs::home_dir())
        .unwrap_or_else(|| PathBuf::from("."));

    base.join("github-gas-gauge").join("config.json")
}

/// Load configuration from disk. Returns default config if the file does not exist.
pub fn load_config() -> Result<AppConfig, String> {
    let path = config_path();
    if !path.exists() {
        return Ok(AppConfig::default());
    }
    let contents =
        fs::read_to_string(&path).map_err(|e| format!("Failed to read config: {}", e))?;
    serde_json::from_str(&contents).map_err(|e| format!("Failed to parse config: {}", e))
}

/// Save configuration to disk, creating directories as needed.
pub fn save_config(config: &AppConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create config directory: {}", e))?;
    }
    let contents =
        serde_json::to_string_pretty(config).map_err(|e| format!("Failed to serialize config: {}", e))?;
    fs::write(&path, contents).map_err(|e| format!("Failed to write config: {}", e))
}
