// GitHub Billing REST API client.
// Fetches Copilot premium request usage and Actions minutes usage.

use serde::{Deserialize, Serialize};

use crate::config::AppConfig;

// ── Response structs ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UsageItem {
    pub product: Option<String>,
    pub model: Option<String>,
    #[serde(rename = "grossQuantity")]
    pub gross_quantity: Option<f64>,
    #[serde(rename = "netQuantity")]
    pub net_quantity: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PremiumRequestUsage {
    #[serde(rename = "usageItems")]
    pub usage_items: Vec<UsageItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActionsMinutesBreakdown {
    #[serde(rename = "UBUNTU")]
    pub ubuntu: Option<u64>,
    #[serde(rename = "MACOS")]
    pub macos: Option<u64>,
    #[serde(rename = "WINDOWS")]
    pub windows: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActionsUsageRaw {
    pub total_minutes_used: Option<f64>,
    pub included_minutes: Option<u64>,
    pub total_paid_minutes_used: Option<f64>,
    pub minutes_used_breakdown: Option<ActionsMinutesBreakdown>,
}

// ── Parsed / normalised structs returned to the frontend ─────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CopilotUsage {
    pub used: u64,
    pub quota: u64,
    pub percent_used: f64,
    pub by_model: std::collections::HashMap<String, u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActionsUsage {
    pub minutes_used: u64,
    pub included_minutes: u64,
    pub paid_minutes_used: u64,
    pub percent_used: f64,
    pub ubuntu_minutes: u64,
    pub macos_minutes: u64,
    pub windows_minutes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BillingData {
    pub copilot: Option<CopilotUsage>,
    pub actions: Option<ActionsUsage>,
}

// ── API helpers ───────────────────────────────────────────────────────────────

const GITHUB_API_BASE: &str = "https://api.github.com";
const API_VERSION: &str = "2022-11-28";

fn make_client(token: &str) -> Result<reqwest::Client, String> {
    let mut headers = reqwest::header::HeaderMap::new();
    headers.insert(
        reqwest::header::AUTHORIZATION,
        format!("Bearer {token}")
            .parse()
            .map_err(|e: reqwest::header::InvalidHeaderValue| e.to_string())?,
    );
    headers.insert(
        reqwest::header::ACCEPT,
        "application/vnd.github+json"
            .parse()
            .map_err(|e: reqwest::header::InvalidHeaderValue| e.to_string())?,
    );
    headers.insert(
        "X-GitHub-Api-Version",
        API_VERSION
            .parse()
            .map_err(|e: reqwest::header::InvalidHeaderValue| e.to_string())?,
    );

    reqwest::Client::builder()
        .default_headers(headers)
        .user_agent("github-gas-gauge/0.1")
        .build()
        .map_err(|e| e.to_string())
}

async fn get_user_copilot_usage(token: &str) -> Result<Option<PremiumRequestUsage>, String> {
    let client = make_client(token)?;
    let resp = client
        .get(format!("{GITHUB_API_BASE}/users/billing/premium_request/usage"))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if resp.status().as_u16() == 404 {
        return Ok(None);
    }

    resp.error_for_status_ref()
        .map_err(|e| e.to_string())?;
    Ok(Some(resp.json::<PremiumRequestUsage>().await.map_err(|e| e.to_string())?))
}

async fn get_org_copilot_usage(token: &str, org: &str) -> Result<Option<PremiumRequestUsage>, String> {
    let client = make_client(token)?;
    let resp = client
        .get(format!(
            "{GITHUB_API_BASE}/organizations/{org}/settings/billing/premium_request/usage"
        ))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let status = resp.status().as_u16();
    if status == 403 || status == 404 {
        return Ok(None);
    }

    resp.error_for_status_ref()
        .map_err(|e| e.to_string())?;
    Ok(Some(resp.json::<PremiumRequestUsage>().await.map_err(|e| e.to_string())?))
}

async fn get_user_actions_usage(token: &str) -> Result<Option<ActionsUsageRaw>, String> {
    let client = make_client(token)?;
    let resp = client
        .get(format!("{GITHUB_API_BASE}/user/settings/billing/actions"))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let status = resp.status().as_u16();
    if status == 403 || status == 404 {
        return Ok(None);
    }

    resp.error_for_status_ref()
        .map_err(|e| e.to_string())?;
    Ok(Some(resp.json::<ActionsUsageRaw>().await.map_err(|e| e.to_string())?))
}

async fn get_org_actions_usage(token: &str, org: &str) -> Result<Option<ActionsUsageRaw>, String> {
    let client = make_client(token)?;
    let resp = client
        .get(format!(
            "{GITHUB_API_BASE}/orgs/{org}/settings/billing/actions"
        ))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let status = resp.status().as_u16();
    if status == 403 || status == 404 {
        return Ok(None);
    }

    resp.error_for_status_ref()
        .map_err(|e| e.to_string())?;
    Ok(Some(resp.json::<ActionsUsageRaw>().await.map_err(|e| e.to_string())?))
}

// ── Parsers ───────────────────────────────────────────────────────────────────

fn parse_copilot(raw: PremiumRequestUsage, quota: u64) -> CopilotUsage {
    let mut used: u64 = 0;
    let mut by_model = std::collections::HashMap::new();

    for item in &raw.usage_items {
        let gross = item.gross_quantity.unwrap_or(0.0) as u64;
        used += gross;
        let model = item.model.clone().unwrap_or_else(|| "unknown".to_string());
        *by_model.entry(model).or_insert(0u64) += gross;
    }

    let percent_used = if quota > 0 {
        (used as f64 / quota as f64).min(1.0)
    } else {
        0.0
    };

    CopilotUsage {
        used,
        quota,
        percent_used,
        by_model,
    }
}

fn parse_actions(raw: ActionsUsageRaw) -> ActionsUsage {
    let minutes_used = raw.total_minutes_used.unwrap_or(0.0) as u64;
    let included_minutes = raw.included_minutes.unwrap_or(0);
    let paid_minutes_used = raw.total_paid_minutes_used.unwrap_or(0.0) as u64;
    let breakdown = raw.minutes_used_breakdown.unwrap_or_default();

    let percent_used = if included_minutes > 0 {
        (minutes_used as f64 / included_minutes as f64).min(1.0)
    } else {
        0.0
    };

    ActionsUsage {
        minutes_used,
        included_minutes,
        paid_minutes_used,
        percent_used,
        ubuntu_minutes: breakdown.ubuntu.unwrap_or(0),
        macos_minutes: breakdown.macos.unwrap_or(0),
        windows_minutes: breakdown.windows.unwrap_or(0),
    }
}

// ── Public fetch entry point ──────────────────────────────────────────────────

pub async fn fetch_billing_data(config: &AppConfig) -> Result<BillingData, String> {
    if config.token.is_empty() {
        return Err("No GitHub token configured. Please add your token in Settings.".to_string());
    }

    let copilot_raw = if config.use_org {
        get_org_copilot_usage(&config.token, &config.org_name).await?
    } else {
        get_user_copilot_usage(&config.token).await?
    };

    let actions_raw = if config.use_org {
        get_org_actions_usage(&config.token, &config.org_name).await?
    } else {
        get_user_actions_usage(&config.token).await?
    };

    let copilot = copilot_raw.map(|raw| parse_copilot(raw, config.copilot_quota));
    let actions = actions_raw.map(parse_actions);

    Ok(BillingData { copilot, actions })
}
