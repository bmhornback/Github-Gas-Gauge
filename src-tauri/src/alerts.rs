// Threshold alert logic — fires OS desktop notifications at 75%, 90%, 100%
// and tracks which thresholds have already been fired this session.

use tauri::{AppHandle, Runtime};
use tauri_plugin_notification::NotificationExt;

use crate::billing::BillingData;
use crate::config::AppConfig;

#[derive(Debug, Default)]
pub struct AlertTracker {
    copilot_75_fired: bool,
    copilot_90_fired: bool,
    copilot_100_fired: bool,
    actions_75_fired: bool,
    actions_90_fired: bool,
    actions_100_fired: bool,
}

impl AlertTracker {
    pub fn new() -> Self {
        Self::default()
    }
}

fn fire_notification<R: Runtime>(app: &AppHandle<R>, title: &str, body: &str) {
    let _ = app
        .notification()
        .builder()
        .title(title)
        .body(body)
        .show();
}

pub fn check_and_fire<R: Runtime>(
    app: &AppHandle<R>,
    data: &BillingData,
    config: &AppConfig,
    tracker: &mut AlertTracker,
) {
    if let Some(copilot) = &data.copilot {
        let pct = copilot.percent_used;

        if config.alert_100 && pct >= 1.0 && !tracker.copilot_100_fired {
            fire_notification(
                app,
                "🔴 Copilot Quota Exhausted",
                &format!(
                    "You've used all {} premium requests this month.",
                    copilot.quota
                ),
            );
            tracker.copilot_100_fired = true;
        } else if config.alert_90 && pct >= 0.90 && !tracker.copilot_90_fired {
            fire_notification(
                app,
                "🟡 Copilot at 90%",
                &format!(
                    "You've used {:.0}% of your {} monthly premium requests.",
                    pct * 100.0,
                    copilot.quota
                ),
            );
            tracker.copilot_90_fired = true;
        } else if config.alert_75 && pct >= 0.75 && !tracker.copilot_75_fired {
            fire_notification(
                app,
                "🟢 Copilot at 75%",
                &format!(
                    "You've used {:.0}% of your {} monthly premium requests.",
                    pct * 100.0,
                    copilot.quota
                ),
            );
            tracker.copilot_75_fired = true;
        }
    }

    if let Some(actions) = &data.actions {
        let pct = actions.percent_used;

        if config.alert_100 && pct >= 1.0 && !tracker.actions_100_fired {
            fire_notification(
                app,
                "🔴 Actions Minutes Exhausted",
                &format!(
                    "You've used all {} included Actions minutes this month.",
                    actions.included_minutes
                ),
            );
            tracker.actions_100_fired = true;
        } else if config.alert_90 && pct >= 0.90 && !tracker.actions_90_fired {
            fire_notification(
                app,
                "🟡 Actions Minutes at 90%",
                &format!(
                    "You've used {:.0}% of your {} included Actions minutes.",
                    pct * 100.0,
                    actions.included_minutes
                ),
            );
            tracker.actions_90_fired = true;
        } else if config.alert_75 && pct >= 0.75 && !tracker.actions_75_fired {
            fire_notification(
                app,
                "🟢 Actions Minutes at 75%",
                &format!(
                    "You've used {:.0}% of your {} included Actions minutes.",
                    pct * 100.0,
                    actions.included_minutes
                ),
            );
            tracker.actions_75_fired = true;
        }
    }
}
