use std::collections::HashSet;
use std::sync::Mutex;

/// Tracks which percentage thresholds have already fired a notification this session.
pub struct AlertTracker {
    notified: Mutex<HashSet<u8>>,
}

impl AlertTracker {
    pub fn new() -> Self {
        Self {
            notified: Mutex::new(HashSet::new()),
        }
    }

    /// Reset all notified thresholds (e.g. at start of new billing period).
    pub fn reset(&self) {
        if let Ok(mut set) = self.notified.lock() {
            set.clear();
        }
    }

    /// Returns whether the given threshold percentage has already been notified.
    pub fn already_notified(&self, threshold: u8) -> bool {
        self.notified
            .lock()
            .map(|set| set.contains(&threshold))
            .unwrap_or(false)
    }

    /// Mark a threshold as notified so it won't fire again.
    pub fn mark_notified(&self, threshold: u8) {
        if let Ok(mut set) = self.notified.lock() {
            set.insert(threshold);
        }
    }
}

impl Default for AlertTracker {
    fn default() -> Self {
        Self::new()
    }
}

/// Returns the threshold levels (in percent) that should fire for a given usage percentage,
/// respecting which thresholds have already been notified and which are enabled.
pub fn thresholds_to_fire(
    usage_pct: f64,
    notify_75: bool,
    notify_90: bool,
    notify_100: bool,
    tracker: &AlertTracker,
) -> Vec<u8> {
    let mut to_fire = Vec::new();

    let candidates: &[(u8, bool)] = &[
        (75, notify_75),
        (90, notify_90),
        (100, notify_100),
    ];

    for &(threshold, enabled) in candidates {
        if enabled && usage_pct >= threshold as f64 && !tracker.already_notified(threshold) {
            to_fire.push(threshold);
        }
    }

    to_fire
}
