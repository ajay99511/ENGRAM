// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::{
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, RunEvent,
};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::path::PathBuf;
use std::fs::OpenOptions;

struct ApiProcess(Arc<Mutex<Option<Child>>>);

fn find_project_root(start: PathBuf) -> PathBuf {
    let mut current = start;
    loop {
        if current.join("packages").exists() && current.join("apps").exists() {
            return current;
        }
        if !current.pop() {
            break;
        }
    }
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn should_autostart() -> bool {
    match std::env::var("PERSONALASSIST_API_AUTOSTART") {
        Ok(val) => {
            let v = val.to_lowercase();
            !(v == "0" || v == "false" || v == "no")
        }
        Err(_) => true,
    }
}

fn spawn_api_process() -> Option<Child> {
    if !should_autostart() {
        return None;
    }

    let cwd = find_project_root(std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    let python = std::env::var("PERSONALASSIST_PYTHON").unwrap_or_else(|_| "python".to_string());
    let host = std::env::var("API_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = std::env::var("API_PORT").unwrap_or_else(|_| "8000".to_string());

    let log_path = std::env::var("PERSONALASSIST_API_LOG").ok()
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
            home.join(".personalassist").join("backend_logs.txt")
        });

    if let Some(parent) = log_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
        .ok();

    let mut cmd = Command::new(python);
    cmd.args([
        "-m",
        "uvicorn",
        "apps.api.main:app",
        "--host",
        &host,
        "--port",
        &port,
    ])
    .current_dir(cwd)
    .stdin(Stdio::null());

    if let Some(file) = log_file {
        let file_err = file.try_clone().ok();
        cmd.stdout(Stdio::from(file));
        if let Some(err) = file_err {
            cmd.stderr(Stdio::from(err));
        }
    }

    cmd.spawn().ok()
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let api_process: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let api_process_clone = api_process.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(ApiProcess(api_process.clone()))
        .setup(move |app| {
            if let Ok(mut guard) = api_process.lock() {
                *guard = spawn_api_process();
            }
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .on_tray_icon_event(|tray, event| match event {
                    TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } => {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let is_visible = window.is_visible().unwrap_or(false);
                            if is_visible {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                    _ => {}
                })
                .build(app)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit { .. }) {
                if let Ok(mut guard) = api_process_clone.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        });
}
