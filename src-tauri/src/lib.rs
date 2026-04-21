pub mod billing;
pub mod config;
pub mod alerts;
pub mod session;

use std::sync::Mutex;

use billing::BillingData;
use alerts::AlertTracker;

/// Shared application state managed by Tauri.
pub struct AppState {
    pub alert_tracker: AlertTracker,
    pub last_billing_data: Mutex<Option<BillingData>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            alert_tracker: AlertTracker::new(),
            last_billing_data: Mutex::new(None),
        }
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}
