#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod engine;
#[cfg(feature = "native-smoke")]
mod smoke;
use engine::Engine;
use serde_json::Value;
use std::{path::PathBuf, sync::Arc};
use tauri::Manager;
use tauri_plugin_dialog::DialogExt;

struct Desktop {
    engine: Result<Arc<Engine>, String>,
}

fn project_link(destination: &str) -> Result<&'static str, String> {
    match destination {
        "docs" => Ok("https://mrueda.github.io/pad-lattice/"),
        "github" => Ok("https://github.com/mrueda/pad-lattice"),
        _ => Err("Unknown project link".into()),
    }
}

#[tauri::command]
async fn open_project_link(destination: String) -> Result<(), String> {
    let url = project_link(&destination)?;
    tauri::async_runtime::spawn_blocking(move || {
        let opener = if cfg!(target_os = "macos") {
            "/usr/bin/open"
        } else {
            "xdg-open"
        };
        let status = std::process::Command::new(opener)
            .arg(url)
            .status()
            .map_err(|e| e.to_string())?;
        if status.success() {
            Ok(())
        } else {
            Err("Could not open your browser".into())
        }
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn desktop_request(
    app: tauri::AppHandle,
    method: String,
    params: Value,
) -> Result<Value, String> {
    let engine = app.state::<Desktop>().engine.clone()?;
    tauri::async_runtime::spawn_blocking(move || engine.request(&method, params))
        .await
        .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn choose_path(app: tauri::AppHandle) -> Result<Option<String>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let picker = app.dialog().file();
        let selected = picker.blocking_pick_file();
        selected
            .map(|path| {
                path.into_path()
                    .map(|p| p.to_string_lossy().into_owned())
                    .map_err(|e| e.to_string())
            })
            .transpose()
    })
    .await
    .map_err(|e| e.to_string())?
}

fn main() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init());
    #[cfg(not(feature = "native-smoke"))]
    let builder = builder.invoke_handler(tauri::generate_handler![
        desktop_request,
        choose_path,
        open_project_link
    ]);
    #[cfg(feature = "native-smoke")]
    let builder = builder
        .invoke_handler(tauri::generate_handler![
            desktop_request,
            choose_path,
            open_project_link,
            smoke::smoke_checkpoint,
            smoke::smoke_finish
        ])
        .on_page_load(|window, payload| {
            if payload.event() == tauri::webview::PageLoadEvent::Finished
                && std::env::var_os("PAD_LATTICE_SMOKE_DIR").is_some()
            {
                let _ = window.eval(smoke::SCRIPT);
            }
        });
    builder
        .setup(|app| {
            let data = app.path().app_data_dir()?;
            #[cfg(feature = "native-smoke")]
            let data = if std::env::var_os("PAD_LATTICE_SMOKE_DIR").is_some() {
                smoke::directory().join("app-data")
            } else {
                data
            };
            std::fs::create_dir_all(&data)?;
            let executable = if cfg!(debug_assertions) {
                PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("engine/pad-lattice-engine")
            } else {
                app.path().resource_dir()?.join("engine/pad-lattice-engine")
            };
            let engine = Engine::start(app.handle().clone(), &executable, &data).map(Arc::new);
            app.manage(Desktop { engine });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Cannot create Pad-Lattice desktop window")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                if let Ok(engine) = &app.state::<Desktop>().engine {
                    engine.stop();
                }
            }
        });
}

#[cfg(test)]
mod tests {
    #[test]
    fn project_links_are_fixed_not_arbitrary_urls() {
        assert!(super::project_link("docs").unwrap().starts_with("https://"));
        assert!(super::project_link("github").is_ok());
        assert!(super::project_link("file:///etc/passwd").is_err());
        assert!(super::project_link("https://example.com").is_err());
    }
}
