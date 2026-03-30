// GitHub Gas Gauge - Rust backend entry point
// Handles system tray, background polling, and Tauri command registration.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod alerts;
mod billing;
mod config;

use std::sync::{Arc, Mutex};
use std::time::Duration;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, Runtime,
};

use crate::alerts::AlertTracker;
use crate::billing::{fetch_billing_data, BillingData};
use crate::config::{load_config_inner, AppConfig};

pub struct AppState {
    pub config: Mutex<AppConfig>,
    pub last_data: Mutex<Option<BillingData>>,
    pub alert_tracker: Mutex<AlertTracker>,
}

// ── Tauri commands ─────────────────────────────────────────────────────────────

#[tauri::command]
async fn get_billing_data(state: tauri::State<'_, Arc<AppState>>) -> Result<BillingData, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    let data = fetch_billing_data(&config).await?;
    *state.last_data.lock().map_err(|e| e.to_string())? = Some(data.clone());
    Ok(data)
}

#[tauri::command]
fn get_config(state: tauri::State<'_, Arc<AppState>>) -> Result<AppConfig, String> {
    let cfg = state.config.lock().map_err(|e| e.to_string())?.clone();
    Ok(cfg)
}

#[tauri::command]
fn save_config(
    new_config: AppConfig,
    state: tauri::State<'_, Arc<AppState>>,
) -> Result<(), String> {
    config::save_config_inner(&new_config)?;
    *state.config.lock().map_err(|e| e.to_string())? = new_config;
    Ok(())
}

#[tauri::command]
async fn refresh_now(state: tauri::State<'_, Arc<AppState>>) -> Result<BillingData, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    let data = fetch_billing_data(&config).await?;
    *state.last_data.lock().map_err(|e| e.to_string())? = Some(data.clone());
    Ok(data)
}

// ── Tray icon helpers ──────────────────────────────────────────────────────────

fn tray_icon_for_pct(pct: f64) -> &'static str {
    if pct >= 0.90 {
        "icons/tray-red.png"
    } else if pct >= 0.75 {
        "icons/tray-yellow.png"
    } else {
        "icons/tray-green.png"
    }
}

fn update_tray_icon<R: Runtime>(app: &AppHandle<R>, pct: f64) {
    if let Some(tray) = app.tray_by_id("main") {
        let icon_path = tray_icon_for_pct(pct);
        if let Ok(icon) = tauri::image::Image::from_path(
            app.path().resource_dir().unwrap_or_default().join(icon_path),
        ) {
            let _ = tray.set_icon(Some(icon));
        }
    }
}

// ── Background polling loop ───────────────────────────────────────────────────

fn start_polling(app: AppHandle, state: Arc<AppState>) {
    tokio::spawn(async move {
        loop {
            let interval_mins = {
                state
                    .config
                    .lock()
                    .map(|c| c.poll_interval_minutes)
                    .unwrap_or(15)
            };
            tokio::time::sleep(Duration::from_secs(interval_mins as u64 * 60)).await;

            let config = match state.config.lock() {
                Ok(c) => c.clone(),
                Err(_) => continue,
            };

            if config.token.is_empty() {
                continue;
            }

            match fetch_billing_data(&config).await {
                Ok(data) => {
                    let copilot_pct = data.copilot.as_ref().map_or(0.0, |c| c.percent_used);

                    update_tray_icon(&app, copilot_pct);

                    if let Ok(mut tracker) = state.alert_tracker.lock() {
                        if let Ok(cfg) = state.config.lock() {
                            alerts::check_and_fire(&app, &data, &cfg, &mut tracker);
                        }
                    }

                    if let Ok(mut last) = state.last_data.lock() {
                        *last = Some(data.clone());
                    }

                    let _ = app.emit("billing-updated", &data);
                }
                Err(e) => {
                    eprintln!("Polling error: {e}");
                }
            }
        }
    });
}

// ── Main entry point ──────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let config = load_config_inner().unwrap_or_default();
    let state = Arc::new(AppState {
        config: Mutex::new(config),
        last_data: Mutex::new(None),
        alert_tracker: Mutex::new(AlertTracker::new()),
    });

    let state_clone = Arc::clone(&state);

    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .manage(state)
        .setup(move |app| {
            let app_handle = app.handle().clone();

            // Build system tray menu
            let open_item = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
            let refresh_item =
                MenuItem::with_id(app, "refresh", "Refresh Now", true, None::<&str>)?;
            let settings_item =
                MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

            let menu = Menu::with_items(
                app,
                &[&open_item, &refresh_item, &settings_item, &quit_item],
            )?;

            TrayIconBuilder::with_id("main")
                .menu(&menu)
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "open" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "refresh" => {
                        let state = app.state::<Arc<AppState>>();
                        let cfg = state.config.lock().unwrap().clone();
                        let app2 = app.clone();
                        tokio::spawn(async move {
                            if let Ok(data) = fetch_billing_data(&cfg).await {
                                let _ = app2.emit("billing-updated", &data);
                            }
                        });
                    }
                    "settings" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            let _ = app.emit("navigate-to-settings", ());
                        }
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

            start_polling(app_handle, state_clone);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_billing_data,
            get_config,
            save_config,
            refresh_now,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
