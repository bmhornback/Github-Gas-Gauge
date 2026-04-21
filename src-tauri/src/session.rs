//! Local Copilot session analytics.
//!
//! Reads session files from `~/.copilot/session-state/` to report token
//! consumption per model, project, and session.
//!
//! Only output tokens are available in Copilot session logs; input tokens are
//! not recorded by Copilot. All processing is local-only — no data is uploaded
//! or transmitted to any external service.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

// ─── Public types ─────────────────────────────────────────────────────────────

/// A single top-session entry ranked by output-token consumption.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SessionSummary {
    pub session_id: String,
    pub project: String,
    pub output_tokens: u64,
    pub model: String,
    pub first_ts: String,
}

/// One day's aggregated output-token count (for the daily trend chart).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DailyUsage {
    pub date: String,
    pub output_tokens: u64,
}

/// Aggregated session analytics returned to the frontend.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SessionAnalytics {
    /// Whether session data was successfully read.
    pub available: bool,
    /// The directory that was scanned.
    pub session_dir: String,
    /// Total output tokens across all sessions.
    pub total_output_tokens: u64,
    /// Total sessions found on disk.
    pub session_count: usize,
    /// Sessions that contained at least one assistant message.
    pub active_session_count: usize,
    /// Output tokens grouped by model name.
    pub by_model: HashMap<String, u64>,
    /// Output tokens grouped by project name.
    pub by_project: HashMap<String, u64>,
    /// Up to 10 top sessions sorted by output tokens descending.
    pub top_sessions: Vec<SessionSummary>,
    /// Daily totals sorted chronologically.
    pub daily_trend: Vec<DailyUsage>,
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

/// Extract the `cwd:` field from a minimal YAML string.
fn parse_cwd_from_yaml(yaml: &str) -> Option<String> {
    for line in yaml.lines() {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("cwd:") {
            // Strip trailing comment, then surrounding quotes / whitespace.
            let raw = rest.split('#').next().unwrap_or("").trim();
            let raw = raw.trim_matches(|c| c == '\'' || c == '"').trim();
            if !raw.is_empty() {
                return Some(raw.to_string());
            }
        }
    }
    None
}

/// Extract the `YYYY-MM-DD` prefix from an ISO-8601 timestamp string.
fn date_from_timestamp(ts: &str) -> Option<String> {
    if ts.len() < 10 {
        return None;
    }
    let d = &ts[..10];
    // Quick sanity check: positions 4 and 7 should be '-'.
    if d.as_bytes().get(4) == Some(&b'-') && d.as_bytes().get(7) == Some(&b'-') {
        return Some(d.to_string());
    }
    None
}

/// Parse an `events.jsonl` file and return assistant-message records.
///
/// Each record is a `serde_json::Value` object with:
///   `model` (string), `output_tokens` (u64), `timestamp` (string)
fn parse_events_file(events_path: &Path) -> Vec<serde_json::Value> {
    let content = match fs::read_to_string(events_path) {
        Ok(c) => c,
        Err(_) => return vec![],
    };

    let mut calls: Vec<serde_json::Value> = Vec::new();
    let mut current_model = String::new();
    let mut seen_message_ids: std::collections::HashSet<String> =
        std::collections::HashSet::new();

    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let event: serde_json::Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(_) => continue,
        };

        let event_type = event
            .get("type")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        match event_type {
            "session.model_change" => {
                if let Some(new_model) = event
                    .get("data")
                    .and_then(|d| d.get("newModel"))
                    .and_then(|v| v.as_str())
                {
                    if !new_model.is_empty() {
                        current_model = new_model.to_string();
                    }
                }
            }
            "assistant.message" => {
                if current_model.is_empty() {
                    continue;
                }
                let data = match event.get("data") {
                    Some(d) => d,
                    None => continue,
                };

                let output_tokens = data
                    .get("outputTokens")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                if output_tokens == 0 {
                    continue;
                }

                let message_id = data
                    .get("messageId")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                if !message_id.is_empty() && !seen_message_ids.insert(message_id) {
                    continue;
                }

                let ts = event
                    .get("timestamp")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();

                calls.push(serde_json::json!({
                    "model": current_model,
                    "output_tokens": output_tokens,
                    "timestamp": ts,
                }));
            }
            _ => {}
        }
    }

    calls
}

// ─── Public API ───────────────────────────────────────────────────────────────

/// Scan the Copilot session-state directory and aggregate analytics.
///
/// Pass `None` for `session_state_dir` to use the default
/// `~/.copilot/session-state`.
pub fn read_session_analytics(session_state_dir: Option<&Path>) -> SessionAnalytics {
    let default_dir: PathBuf = dirs::home_dir()
        .map(|h| h.join(".copilot").join("session-state"))
        .unwrap_or_else(|| PathBuf::from(".copilot/session-state"));
    let dir: &Path = session_state_dir.unwrap_or(default_dir.as_path());
    let dir_str = dir.to_string_lossy().to_string();

    let read_dir = match fs::read_dir(dir) {
        Ok(rd) => rd,
        Err(_) => {
            return SessionAnalytics {
                available: false,
                session_dir: dir_str,
                ..Default::default()
            };
        }
    };

    let mut total_output_tokens: u64 = 0;
    let mut by_model: HashMap<String, u64> = HashMap::new();
    let mut by_project: HashMap<String, u64> = HashMap::new();
    let mut session_summaries: Vec<SessionSummary> = Vec::new();
    let mut daily: HashMap<String, u64> = HashMap::new();
    let mut session_count: usize = 0;
    let mut active_session_count: usize = 0;

    // Collect and sort entries for deterministic ordering.
    let mut entries: Vec<_> = read_dir.flatten().collect();
    entries.sort_by_key(|e| e.file_name());

    for entry in entries {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        let events_path = path.join("events.jsonl");
        if !events_path.is_file() {
            continue;
        }

        session_count += 1;
        let session_id = path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        // Derive project name from workspace.yaml cwd field, falling back to
        // the session directory name.
        let mut project = session_id.clone();
        let workspace_yaml = path.join("workspace.yaml");
        if workspace_yaml.is_file() {
            if let Ok(yaml) = fs::read_to_string(&workspace_yaml) {
                if let Some(cwd) = parse_cwd_from_yaml(&yaml) {
                    if let Some(name) = Path::new(&cwd).file_name() {
                        project = name.to_string_lossy().to_string();
                    }
                }
            }
        }

        let calls = parse_events_file(&events_path);
        if calls.is_empty() {
            continue;
        }

        active_session_count += 1;
        let mut session_tokens: u64 = 0;
        let mut session_model = String::new();
        let mut first_ts = String::new();

        for call in &calls {
            let tokens = call
                .get("output_tokens")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let model = call
                .get("model")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            let ts = call
                .get("timestamp")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            session_tokens += tokens;
            total_output_tokens += tokens;
            *by_model.entry(model.to_string()).or_insert(0) += tokens;
            *by_project.entry(project.clone()).or_insert(0) += tokens;

            if session_model.is_empty() {
                session_model = model.to_string();
            }
            if first_ts.is_empty() && !ts.is_empty() {
                first_ts = ts.to_string();
            }
            if let Some(date) = date_from_timestamp(ts) {
                *daily.entry(date).or_insert(0) += tokens;
            }
        }

        session_summaries.push(SessionSummary {
            session_id,
            project,
            output_tokens: session_tokens,
            model: session_model,
            first_ts,
        });
    }

    session_summaries.sort_by(|a, b| b.output_tokens.cmp(&a.output_tokens));
    let top_sessions = session_summaries.into_iter().take(10).collect();

    let mut daily_trend: Vec<DailyUsage> = daily
        .into_iter()
        .map(|(date, output_tokens)| DailyUsage { date, output_tokens })
        .collect();
    daily_trend.sort_by(|a, b| a.date.cmp(&b.date));

    SessionAnalytics {
        available: true,
        session_dir: dir_str,
        total_output_tokens,
        session_count,
        active_session_count,
        by_model,
        by_project,
        top_sessions,
        daily_trend,
    }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_cwd_basic() {
        let yaml = "cwd: /home/user/myproject\n";
        assert_eq!(parse_cwd_from_yaml(yaml), Some("/home/user/myproject".to_string()));
    }

    #[test]
    fn test_parse_cwd_with_comment() {
        let yaml = "cwd: /home/user/myproject # workspace root\n";
        assert_eq!(parse_cwd_from_yaml(yaml), Some("/home/user/myproject".to_string()));
    }

    #[test]
    fn test_parse_cwd_with_quotes() {
        let yaml = "cwd: '/home/user/my project'\n";
        assert_eq!(parse_cwd_from_yaml(yaml), Some("/home/user/my project".to_string()));
    }

    #[test]
    fn test_parse_cwd_missing() {
        let yaml = "other: value\n";
        assert_eq!(parse_cwd_from_yaml(yaml), None);
    }

    #[test]
    fn test_date_from_timestamp_valid() {
        assert_eq!(
            date_from_timestamp("2026-04-21T12:34:56Z"),
            Some("2026-04-21".to_string())
        );
    }

    #[test]
    fn test_date_from_timestamp_short() {
        assert_eq!(date_from_timestamp("2026-04"), None);
    }

    #[test]
    fn test_date_from_timestamp_no_dashes() {
        assert_eq!(date_from_timestamp("20260421T123456Z"), None);
    }

    #[test]
    fn test_parse_events_empty() {
        use std::io::Write;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        writeln!(f, "").unwrap();
        assert!(parse_events_file(f.path()).is_empty());
    }

    #[test]
    fn test_parse_events_basic() {
        use std::io::Write;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        writeln!(f, r#"{{"type":"session.model_change","data":{{"newModel":"gpt-4.1"}}}}"#).unwrap();
        writeln!(f, r#"{{"type":"user.message","data":{{"content":"hello"}}}}"#).unwrap();
        writeln!(
            f,
            r#"{{"type":"assistant.message","timestamp":"2026-04-21T10:00:00Z","data":{{"messageId":"msg1","outputTokens":100}}}}"#
        ).unwrap();

        let calls = parse_events_file(f.path());
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0]["model"], "gpt-4.1");
        assert_eq!(calls[0]["output_tokens"], 100);
    }

    #[test]
    fn test_parse_events_skips_zero_tokens() {
        use std::io::Write;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        writeln!(f, r#"{{"type":"session.model_change","data":{{"newModel":"gpt-4.1"}}}}"#).unwrap();
        writeln!(
            f,
            r#"{{"type":"assistant.message","timestamp":"2026-04-21T10:00:00Z","data":{{"messageId":"msg1","outputTokens":0}}}}"#
        ).unwrap();

        assert!(parse_events_file(f.path()).is_empty());
    }

    #[test]
    fn test_parse_events_skips_no_model() {
        use std::io::Write;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        writeln!(
            f,
            r#"{{"type":"assistant.message","timestamp":"2026-04-21T10:00:00Z","data":{{"messageId":"msg1","outputTokens":50}}}}"#
        ).unwrap();

        assert!(parse_events_file(f.path()).is_empty());
    }

    #[test]
    fn test_parse_events_deduplicates_message_ids() {
        use std::io::Write;
        let mut f = tempfile::NamedTempFile::new().unwrap();
        writeln!(f, r#"{{"type":"session.model_change","data":{{"newModel":"gpt-4.1"}}}}"#).unwrap();
        for _ in 0..3 {
            writeln!(
                f,
                r#"{{"type":"assistant.message","timestamp":"2026-04-21T10:00:00Z","data":{{"messageId":"dup","outputTokens":10}}}}"#
            ).unwrap();
        }

        let calls = parse_events_file(f.path());
        assert_eq!(calls.len(), 1);
    }
}
