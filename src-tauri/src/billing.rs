// GitHub Billing REST API client.
// Fetches Copilot premium request usage, Actions minutes usage,
// and external AI provider token/balance data.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::config::AppConfig;

// ── GitHub response structs ───────────────────────────────────────────────────

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

// ── OpenAI billing response structs ──────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OpenAILineItem {
    pub name: Option<String>,
    pub cost: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OpenAIDailyCost {
    pub timestamp: Option<f64>,
    pub line_items: Option<Vec<OpenAILineItem>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OpenAIBillingUsage {
    pub total_usage: Option<f64>,
    pub daily_costs: Option<Vec<OpenAIDailyCost>>,
}

// ── DeepSeek balance response structs ────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DeepSeekBalanceInfo {
    pub currency: Option<String>,
    pub total_balance: Option<String>,
    pub granted_balance: Option<String>,
    pub topped_up_balance: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DeepSeekBalance {
    pub is_available: Option<bool>,
    pub balance_infos: Option<Vec<DeepSeekBalanceInfo>>,
}

// ── Parsed / normalised structs returned to the frontend ─────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CopilotUsage {
    pub used: u64,
    pub quota: u64,
    pub percent_used: f64,
    pub by_model: HashMap<String, u64>,
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

/// Normalised usage data for a single external AI provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderUsage {
    pub provider_id: String,
    pub name: String,
    /// Whether usage data was successfully fetched.
    pub available: bool,
    /// "cost" or "balance"
    pub billing_type: String,
    /// Total spend in USD this period (cost-based providers).
    pub cost_usd: f64,
    /// Remaining credit balance in USD (balance-based providers).
    pub balance_usd: f64,
    /// Currency code for balance-based providers (e.g. "USD", "CNY").
    pub currency: String,
    /// Optional user-defined monthly limit in USD.
    pub limit_usd: Option<f64>,
    /// Percentage used (0.0–1.0). For balance providers: spend / limit.
    pub percent_used: f64,
    /// Per-model cost breakdown (USD).
    pub by_model: HashMap<String, f64>,
    /// Human-readable note when `available` is false.
    pub note: Option<String>,
}

impl Default for ProviderUsage {
    fn default() -> Self {
        Self {
            provider_id: String::new(),
            name: String::new(),
            available: false,
            billing_type: "cost".to_string(),
            cost_usd: 0.0,
            balance_usd: 0.0,
            currency: "USD".to_string(),
            limit_usd: None,
            percent_used: 0.0,
            by_model: HashMap::new(),
            note: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BillingData {
    pub copilot: Option<CopilotUsage>,
    pub actions: Option<ActionsUsage>,
    /// Usage data for all configured external AI providers.
    pub providers: Vec<ProviderUsage>,
}

// ── API helpers ───────────────────────────────────────────────────────────────

const GITHUB_API_BASE: &str = "https://api.github.com";
const API_VERSION: &str = "2022-11-28";

fn make_github_client(token: &str) -> Result<reqwest::Client, String> {
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
    let client = make_github_client(token)?;
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
    let client = make_github_client(token)?;
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
    let client = make_github_client(token)?;
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
    let client = make_github_client(token)?;
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

// ── External provider fetchers ────────────────────────────────────────────────

async fn fetch_openai_usage(api_key: &str, limit_usd: Option<f64>) -> ProviderUsage {
    use chrono::{Datelike, Local};

    let now = Local::now();
    let year = now.year();
    let month = now.month();
    let last_day = days_in_month(year, month as u8);

    let start_date = format!("{year}-{month:02}-01");
    let end_date = format!("{year}-{month:02}-{last_day:02}");

    let client = match reqwest::Client::builder()
        .user_agent("github-gas-gauge/0.1")
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            return ProviderUsage {
                provider_id: "openai".to_string(),
                name: "OpenAI".to_string(),
                note: Some(format!("Failed to build HTTP client: {e}")),
                ..Default::default()
            }
        }
    };

    let resp = client
        .get("https://api.openai.com/v1/dashboard/billing/usage")
        .header(reqwest::header::AUTHORIZATION, format!("Bearer {api_key}"))
        .query(&[("start_date", start_date.as_str()), ("end_date", end_date.as_str())])
        .send()
        .await;

    let resp = match resp {
        Ok(r) => r,
        Err(e) => {
            return ProviderUsage {
                provider_id: "openai".to_string(),
                name: "OpenAI".to_string(),
                note: Some(format!("Request error: {e}")),
                ..Default::default()
            }
        }
    };

    let status = resp.status().as_u16();
    if status == 401 || status == 403 || status == 404 {
        return ProviderUsage {
            provider_id: "openai".to_string(),
            name: "OpenAI".to_string(),
            note: Some(
                "Could not fetch usage. Ensure your API key has billing read access."
                    .to_string(),
            ),
            ..Default::default()
        };
    }

    let data: OpenAIBillingUsage = match resp.json().await {
        Ok(d) => d,
        Err(e) => {
            return ProviderUsage {
                provider_id: "openai".to_string(),
                name: "OpenAI".to_string(),
                note: Some(format!("Failed to parse response: {e}")),
                ..Default::default()
            }
        }
    };

    // total_usage is in USD cents
    let cost_usd = data.total_usage.unwrap_or(0.0) / 100.0;

    let mut by_model: HashMap<String, f64> = HashMap::new();
    for day in data.daily_costs.unwrap_or_default() {
        for item in day.line_items.unwrap_or_default() {
            let name = item.name.unwrap_or_else(|| "unknown".to_string());
            let cost = item.cost.unwrap_or(0.0) / 100.0;
            *by_model.entry(name).or_insert(0.0) += cost;
        }
    }

    let percent_used = limit_usd
        .filter(|&l| l > 0.0)
        .map(|l| (cost_usd / l).min(1.0))
        .unwrap_or(0.0);

    ProviderUsage {
        provider_id: "openai".to_string(),
        name: "OpenAI".to_string(),
        available: true,
        billing_type: "cost".to_string(),
        cost_usd,
        limit_usd,
        percent_used,
        by_model,
        ..Default::default()
    }
}

async fn fetch_deepseek_balance(api_key: &str, limit_usd: Option<f64>) -> ProviderUsage {
    let client = match reqwest::Client::builder()
        .user_agent("github-gas-gauge/0.1")
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            return ProviderUsage {
                provider_id: "deepseek".to_string(),
                name: "DeepSeek".to_string(),
                note: Some(format!("Failed to build HTTP client: {e}")),
                ..Default::default()
            }
        }
    };

    let resp = client
        .get("https://api.deepseek.com/user/balance")
        .header(reqwest::header::AUTHORIZATION, format!("Bearer {api_key}"))
        .header(reqwest::header::ACCEPT, "application/json")
        .send()
        .await;

    let resp = match resp {
        Ok(r) => r,
        Err(e) => {
            return ProviderUsage {
                provider_id: "deepseek".to_string(),
                name: "DeepSeek".to_string(),
                note: Some(format!("Request error: {e}")),
                ..Default::default()
            }
        }
    };

    let status = resp.status().as_u16();
    if status == 401 || status == 403 || status == 404 {
        return ProviderUsage {
            provider_id: "deepseek".to_string(),
            name: "DeepSeek".to_string(),
            note: Some("Could not fetch balance. Check your DeepSeek API key.".to_string()),
            ..Default::default()
        };
    }

    let data: DeepSeekBalance = match resp.json().await {
        Ok(d) => d,
        Err(e) => {
            return ProviderUsage {
                provider_id: "deepseek".to_string(),
                name: "DeepSeek".to_string(),
                note: Some(format!("Failed to parse response: {e}")),
                ..Default::default()
            }
        }
    };

    let balance_infos = data.balance_infos.unwrap_or_default();
    let (balance_usd, currency) = balance_infos
        .first()
        .map(|info| {
            let bal = info
                .total_balance
                .as_deref()
                .and_then(|s| s.parse::<f64>().ok())
                .unwrap_or(0.0);
            let cur = info
                .currency
                .clone()
                .unwrap_or_else(|| "USD".to_string());
            (bal, cur)
        })
        .unwrap_or((0.0, "USD".to_string()));

    let percent_used = limit_usd
        .filter(|&l| l > 0.0)
        .map(|l| ((l - balance_usd) / l).clamp(0.0, 1.0))
        .unwrap_or(0.0);

    ProviderUsage {
        provider_id: "deepseek".to_string(),
        name: "DeepSeek".to_string(),
        available: true,
        billing_type: "balance".to_string(),
        balance_usd,
        currency,
        limit_usd,
        percent_used,
        ..Default::default()
    }
}

fn unavailable_provider(provider_id: &str, name: &str, note: &str) -> ProviderUsage {
    ProviderUsage {
        provider_id: provider_id.to_string(),
        name: name.to_string(),
        note: Some(note.to_string()),
        ..Default::default()
    }
}

/// Helper: number of days in a given month.
fn days_in_month(year: i32, month: u8) -> u8 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            if year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) {
                29
            } else {
                28
            }
        }
        _ => 30,
    }
}

// ── GitHub parsers ────────────────────────────────────────────────────────────

fn parse_copilot(raw: PremiumRequestUsage, quota: u64) -> CopilotUsage {
    let mut used: u64 = 0;
    let mut by_model = HashMap::new();

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

    // Fetch external provider data concurrently
    let providers = fetch_all_providers(config).await;

    Ok(BillingData { copilot, actions, providers })
}

/// Fetch usage data for all configured external AI providers concurrently.
pub async fn fetch_all_providers(config: &AppConfig) -> Vec<ProviderUsage> {
    let mut results = Vec::new();

    // OpenAI
    let openai_key = config.provider_keys.get("openai").cloned().unwrap_or_default();
    if !openai_key.is_empty() {
        let limit = config.provider_limits.get("openai").copied();
        results.push(fetch_openai_usage(&openai_key, limit).await);
    } else {
        results.push(unavailable_provider(
            "openai",
            "OpenAI",
            "Set OPENAI_API_KEY in Settings to enable.",
        ));
    }

    // Anthropic
    let anthropic_key = config.provider_keys.get("anthropic").cloned().unwrap_or_default();
    results.push(unavailable_provider(
        "anthropic",
        "Anthropic",
        if anthropic_key.is_empty() {
            "No public usage API for individual keys. View at https://console.anthropic.com/settings/usage"
        } else {
            "No public usage API for individual keys. View at https://console.anthropic.com/settings/usage"
        },
    ));

    // DeepSeek
    let deepseek_key = config.provider_keys.get("deepseek").cloned().unwrap_or_default();
    if !deepseek_key.is_empty() {
        let limit = config.provider_limits.get("deepseek").copied();
        results.push(fetch_deepseek_balance(&deepseek_key, limit).await);
    } else {
        results.push(unavailable_provider(
            "deepseek",
            "DeepSeek",
            "Set DeepSeek API key in Settings to enable.",
        ));
    }

    // Perplexity
    results.push(unavailable_provider(
        "perplexity",
        "Perplexity",
        "No public usage API available. View at https://www.perplexity.ai/settings/api",
    ));

    // Gemini
    results.push(unavailable_provider(
        "gemini",
        "Google Gemini",
        "No public usage API available. View at https://aistudio.google.com/",
    ));

    results
}

