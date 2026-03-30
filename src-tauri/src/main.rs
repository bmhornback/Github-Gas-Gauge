// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, State,
};

use github_gas_gauge_lib::{alerts, billing, config, AppState};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .manage(AppState::new())
        .invoke_handler(tauri::generate_handler![
            get_billing_data,
            get_config,
            save_config_cmd,
            refresh_now,
        ])
        .setup(|app| {
            // Build system tray menu.
            let open_item =
                MenuItem::with_id(app, "open", "Open GitHub Gas Gauge", true, None::<&str>)?;
            let refresh_item =
                MenuItem::with_id(app, "refresh", "Refresh Now", true, None::<&str>)?;
            let settings_item =
                MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

            let menu = Menu::with_items(
                app,
                &[&open_item, &refresh_item, &settings_item, &quit_item],
            )?;

            let _tray = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("GitHub Gas Gauge")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" | "settings" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "refresh" => {
                        app.emit("refresh-requested", ()).ok();
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running GitHub Gas Gauge");
}

// ─── Tauri Commands ──────────────────────────────────────────────────────────

/// Fetch current billing data from the GitHub API and fire any pending notifications.
#[tauri::command]
fn get_billing_data(
    app: AppHandle,
    state: State<AppState>,
) -> Result<billing::BillingData, String> {
    fetch_and_notify(&app, &state)
}

/// Trigger an immediate billing data refresh (bound to tray "Refresh Now").
#[tauri::command]
fn refresh_now(app: AppHandle, state: State<AppState>) -> Result<billing::BillingData, String> {
    fetch_and_notify(&app, &state)
}

/// Load configuration from disk.
#[tauri::command]
fn get_config() -> Result<config::AppConfig, String> {
    config::load_config()
}

/// Persist configuration to disk.
#[tauri::command]
fn save_config_cmd(new_config: config::AppConfig) -> Result<(), String> {
    config::save_config(&new_config)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

fn fetch_and_notify(
    app: &AppHandle,
    state: &State<AppState>,
) -> Result<billing::BillingData, String> {
    let cfg = config::load_config()?;

    let token = cfg
        .github_pat
        .as_deref()
        .filter(|t| !t.is_empty())
        .ok_or_else(|| {
            "No GitHub PAT configured. Please add your token in Settings.".to_string()
        })?;

    let data = if cfg.use_org {
        let org = cfg
            .org_name
            .as_deref()
            .filter(|o| !o.is_empty())
            .ok_or_else(|| {
                "Organization name is required when org mode is enabled.".to_string()
            })?;
        billing::fetch_org_billing(token, org)?
    } else {
        billing::fetch_user_billing(token)?
    };

    // Cache the latest billing data.
    if let Ok(mut guard) = state.last_billing_data.lock() {
        *guard = Some(data.clone());
    }

    // Determine which thresholds to fire and send OS notifications.
    let usage_pct = data.usage_percentage();
    let thresholds = alerts::thresholds_to_fire(
        usage_pct,
        cfg.alert_thresholds.notify_at_75,
        cfg.alert_thresholds.notify_at_90,
        cfg.alert_thresholds.notify_at_100,
        &state.alert_tracker,
    );

    for threshold in thresholds {
        state.alert_tracker.mark_notified(threshold);
        send_threshold_notification(app, threshold, usage_pct);
    }

    Ok(data)
}

fn send_threshold_notification(app: &AppHandle, threshold: u8, usage_pct: f64) {
    use tauri_plugin_notification::NotificationExt;
    let title = format!("⚠️ GitHub Actions Usage at {}%", threshold);
    let body = format!(
        "You've used {:.1}% of your included Actions minutes. {}",
        usage_pct,
        if threshold >= 100 {
            "You may be incurring overage charges."
        } else {
            "Consider reviewing your workflow usage."
        }
    );
    let _ = app.notification().builder().title(title).body(body).show();
}

