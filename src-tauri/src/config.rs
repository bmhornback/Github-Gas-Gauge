// App configuration — stored as JSON in the OS app-data directory.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const CONFIG_FILE_NAME: &str = "gas-gauge-config.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// GitHub personal access token.
    pub token: String,
    /// Use an organisation rather than the authenticated user.
    pub use_org: bool,
    /// Organisation name (only used when `use_org` is true).
    pub org_name: String,
    /// Polling interval in minutes.
    pub poll_interval_minutes: u64,
    /// Copilot monthly quota (premium requests).
    pub copilot_quota: u64,
    /// Fire notification at 75% usage.
    pub alert_75: bool,
    /// Fire notification at 90% usage.
    pub alert_90: bool,
    /// Fire notification at 100% usage.
    pub alert_100: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            token: String::new(),
            use_org: false,
            org_name: String::new(),
            poll_interval_minutes: 15,
            copilot_quota: 300,
            alert_75: true,
            alert_90: true,
            alert_100: true,
        }
    }
}

fn config_path() -> Option<PathBuf> {
    dirs::config_dir().map(|mut p| {
        p.push("github-gas-gauge");
        p.push(CONFIG_FILE_NAME);
        p
    })
}

pub fn load_config_inner() -> Result<AppConfig, String> {
    let path = config_path().ok_or("Could not determine config directory")?;
    if !path.exists() {
        return Ok(AppConfig::default());
    }
    let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    serde_json::from_str(&text).map_err(|e| e.to_string())
}

pub fn save_config_inner(config: &AppConfig) -> Result<(), String> {
    let path = config_path().ok_or("Could not determine config directory")?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let text = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    std::fs::write(&path, text).map_err(|e| e.to_string())
}
