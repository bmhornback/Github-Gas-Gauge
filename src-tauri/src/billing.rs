use serde::{Deserialize, Serialize};

/// Breakdown of minutes used per runner OS type.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MinutesBreakdown {
    pub ubuntu: f64,
    pub macos: f64,
    pub windows: f64,
}

/// GitHub Actions billing data returned from the API.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BillingData {
    pub total_minutes_used: f64,
    pub total_paid_minutes_used: f64,
    pub included_minutes: f64,
    pub minutes_used_breakdown: MinutesBreakdown,
}

impl BillingData {
    /// Returns the percentage of included minutes consumed (0.0–100.0+).
    pub fn usage_percentage(&self) -> f64 {
        if self.included_minutes == 0.0 {
            return 100.0;
        }
        (self.total_minutes_used / self.included_minutes) * 100.0
    }
}

/// Raw response shape from GitHub's billing API.
#[derive(Debug, Deserialize)]
struct GithubBillingResponse {
    total_minutes_used: Option<f64>,
    total_paid_minutes_used: Option<f64>,
    included_minutes: Option<f64>,
    minutes_used_breakdown: Option<GithubMinutesBreakdown>,
}

#[derive(Debug, Deserialize)]
struct GithubMinutesBreakdown {
    #[serde(rename = "UBUNTU")]
    ubuntu: Option<f64>,
    #[serde(rename = "MACOS")]
    macos: Option<f64>,
    #[serde(rename = "WINDOWS")]
    windows: Option<f64>,
}

/// Fetch Actions billing for a personal user account.
pub fn fetch_user_billing(token: &str) -> Result<BillingData, String> {
    let client = reqwest::blocking::Client::new();
    let url = "https://api.github.com/user/settings/billing/actions";
    let response = client
        .get(url)
        .header("Authorization", format!("Bearer {}", token))
        .header("User-Agent", "GitHub-Gas-Gauge/0.1.0")
        .header("Accept", "application/vnd.github+json")
        .header("X-GitHub-Api-Version", "2022-11-28")
        .send()
        .map_err(|e| format!("Network error: {}", e))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().unwrap_or_default();
        return Err(format!("GitHub API error {}: {}", status, body));
    }

    let raw: GithubBillingResponse = response
        .json()
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    Ok(parse_response(raw))
}

/// Fetch Actions billing for an organization account.
pub fn fetch_org_billing(token: &str, org: &str) -> Result<BillingData, String> {
    let client = reqwest::blocking::Client::new();
    let url = format!(
        "https://api.github.com/orgs/{}/settings/billing/actions",
        org
    );
    let response = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", token))
        .header("User-Agent", "GitHub-Gas-Gauge/0.1.0")
        .header("Accept", "application/vnd.github+json")
        .header("X-GitHub-Api-Version", "2022-11-28")
        .send()
        .map_err(|e| format!("Network error: {}", e))?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().unwrap_or_default();
        return Err(format!("GitHub API error {}: {}", status, body));
    }

    let raw: GithubBillingResponse = response
        .json()
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    Ok(parse_response(raw))
}

fn parse_response(raw: GithubBillingResponse) -> BillingData {
    let breakdown = raw
        .minutes_used_breakdown
        .map(|b| MinutesBreakdown {
            ubuntu: b.ubuntu.unwrap_or(0.0),
            macos: b.macos.unwrap_or(0.0),
            windows: b.windows.unwrap_or(0.0),
        })
        .unwrap_or_default();

    BillingData {
        total_minutes_used: raw.total_minutes_used.unwrap_or(0.0),
        total_paid_minutes_used: raw.total_paid_minutes_used.unwrap_or(0.0),
        included_minutes: raw.included_minutes.unwrap_or(0.0),
        minutes_used_breakdown: breakdown,
    }
}
