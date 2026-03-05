/** TeleMU Tauri shell — window management, tray, IPC, backend lifecycle. */

use std::sync::{Arc, Mutex};
use tauri::{
    image::Image,
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, Runtime,
};

// ---------------------------------------------------------------------------
// Shared tray state
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, Default)]
struct TrayStatus {
    connected: bool,
    recording: bool,
}

type SharedTrayStatus = Arc<Mutex<TrayStatus>>;

// ---------------------------------------------------------------------------
// Icon helpers
// ---------------------------------------------------------------------------

fn tray_icon_bytes(status: &TrayStatus) -> &'static [u8] {
    if status.recording {
        include_bytes!("../icons/tray-recording.png")
    } else if status.connected {
        include_bytes!("../icons/tray-connected.png")
    } else {
        include_bytes!("../icons/tray-disconnected.png")
    }
}

fn tray_tooltip(status: &TrayStatus) -> String {
    let conn = if status.connected { "Connected" } else { "Disconnected" };
    if status.recording {
        format!("TeleMU — {} — Recording", conn)
    } else {
        format!("TeleMU — {}", conn)
    }
}

// ---------------------------------------------------------------------------
// Tauri commands (called by the renderer via invoke)
// ---------------------------------------------------------------------------

/// Renderer calls this to update the tray icon and tooltip.
#[tauri::command]
fn update_tray_status<R: Runtime>(
    app: AppHandle<R>,
    connected: bool,
    recording: bool,
    tray_status: tauri::State<'_, SharedTrayStatus>,
) {
    let new_status = TrayStatus { connected, recording };

    if let Ok(mut guard) = tray_status.lock() {
        *guard = new_status.clone();
    }

    if let Some(tray) = app.tray_by_id("main") {
        let icon = Image::from_bytes(tray_icon_bytes(&new_status))
            .expect("failed to load tray icon");
        let _ = tray.set_icon(Some(icon));
        let _ = tray.set_tooltip(Some(&tray_tooltip(&new_status)));
    }
}

/// Renderer requests to toggle minimize-to-tray behaviour (no-op in Tauri;
/// handled by the close-requested handler set up in `setup`).
#[tauri::command]
fn set_minimize_to_tray(_value: bool) {}

/// Renderer requests to set whether the app starts minimized (no-op; handled
/// at startup via tauri.conf.json `visible` flag or equivalent).
#[tauri::command]
fn set_start_minimized(_value: bool) {}

// ---------------------------------------------------------------------------
// Backend sidecar lifecycle
// ---------------------------------------------------------------------------

#[cfg(not(debug_assertions))]
fn spawn_backend(app: &AppHandle) {
    // In production, the backend exe is bundled as a resource next to the app.
    let resource_dir = match app.path().resource_dir() {
        Ok(dir) => dir,
        Err(e) => {
            eprintln!("Failed to get resource directory: {e}");
            // Fall back to the directory containing the Tauri binary
            if let Ok(mut exe) = std::env::current_exe() {
                exe.pop();
                exe
            } else {
                return;
            }
        }
    };

    #[cfg(target_os = "windows")]
    let backend_name = "telemu-backend.exe";
    #[cfg(not(target_os = "windows"))]
    let backend_name = "telemu-backend";

    let backend_path = resource_dir.join(backend_name);
    if backend_path.exists() {
        let _ = std::process::Command::new(&backend_path)
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn();
    } else {
        eprintln!("Backend executable not found at {:?}", backend_path);
    }
}

// ---------------------------------------------------------------------------
// Tray context menu
// ---------------------------------------------------------------------------

fn build_tray_menu<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<Menu<R>> {
    let toggle_recording =
        MenuItem::with_id(app, "toggle-recording", "Toggle Recording", true, None::<&str>)?;
    let toggle_conn =
        MenuItem::with_id(app, "toggle-connection", "Toggle Connection", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let open = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
    let separator2 = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    Menu::with_items(
        app,
        &[
            &toggle_recording,
            &toggle_conn,
            &separator,
            &open,
            &separator2,
            &quit,
        ],
    )
}

// ---------------------------------------------------------------------------
// App entry point
// ---------------------------------------------------------------------------

pub fn run() {
    let tray_status: SharedTrayStatus = Arc::new(Mutex::new(TrayStatus::default()));

    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .manage(tray_status)
        .setup(|app| {
            // Spawn backend sidecar in production builds only
            #[cfg(not(debug_assertions))]
            spawn_backend(app.handle());

            // Build system tray
            let status = TrayStatus::default();
            let icon = Image::from_bytes(tray_icon_bytes(&status))
                .expect("failed to load tray icon");
            let menu = build_tray_menu(app.handle())?;

            let handle = app.handle().clone();
            TrayIconBuilder::with_id("main")
                .icon(icon)
                .tooltip(tray_tooltip(&status))
                .menu(&menu)
                .on_menu_event(move |_tray, event| {
                    match event.id.as_ref() {
                        "toggle-recording" => {
                            let _ = handle.emit("tray://toggle-recording", ());
                        }
                        "toggle-connection" => {
                            let _ = handle.emit("tray://toggle-connection", ());
                        }
                        "open" => {
                            if let Some(win) = handle.get_webview_window("main") {
                                let _ = win.show();
                                let _ = win.set_focus();
                            }
                        }
                        "quit" => {
                            handle.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(win) = app.get_webview_window("main") {
                            let _ = win.show();
                            let _ = win.set_focus();
                        }
                    }
                })
                .build(app)?;

            // Minimize to tray on close instead of quitting
            let app_handle = app.handle().clone();
            if let Some(win) = app.get_webview_window("main") {
                win.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        if let Some(w) = app_handle.get_webview_window("main") {
                            let _ = w.hide();
                        }
                    }
                });
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            update_tray_status,
            set_minimize_to_tray,
            set_start_minimized,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
