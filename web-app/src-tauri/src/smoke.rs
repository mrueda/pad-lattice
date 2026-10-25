//! Native UI verification, compiled only for explicit test builds.
use serde_json::{json, Value};
use std::{path::PathBuf, time::Duration};
use tauri::Manager;

pub fn directory() -> PathBuf {
    PathBuf::from(std::env::var_os("PAD_LATTICE_SMOKE_DIR").unwrap())
}

#[tauri::command]
pub async fn smoke_checkpoint(
    app: tauri::AppHandle,
    label: String,
    details: Value,
) -> Result<(), String> {
    if label.is_empty()
        || !label
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'-')
    {
        return Err("Invalid checkpoint".into());
    }
    let directory = directory();
    std::fs::create_dir_all(&directory).map_err(|e| e.to_string())?;
    std::fs::write(
        directory.join(format!("{label}.json")),
        serde_json::to_vec_pretty(&details).unwrap(),
    )
    .map_err(|e| e.to_string())?;
    #[cfg(target_os = "linux")]
    {
        use webkit2gtk::WebViewExt;
        let (tx, rx) = std::sync::mpsc::channel();
        let target = directory.join(format!("{label}.png"));
        app.get_webview_window("main")
            .ok_or("Missing window")?
            .with_webview(move |webview| {
                webview.inner().snapshot(
                    webkit2gtk::SnapshotRegion::Visible,
                    webkit2gtk::SnapshotOptions::NONE,
                    None::<&webkit2gtk::gio::Cancellable>,
                    move |result| {
                        let result = result.map_err(|e| e.to_string()).and_then(|surface| {
                            let mut file =
                                std::fs::File::create(target).map_err(|e| e.to_string())?;
                            surface.write_to_png(&mut file).map_err(|e| e.to_string())
                        });
                        let _ = tx.send(result);
                    },
                );
            })
            .map_err(|e| e.to_string())?;
        tauri::async_runtime::spawn_blocking(move || {
            rx.recv_timeout(Duration::from_secs(10))
                .map_err(|e| e.to_string())?
        })
        .await
        .map_err(|e| e.to_string())??;
    }
    Ok(())
}

#[tauri::command]
pub fn smoke_finish(app: tauri::AppHandle, error: Option<String>) {
    let _ = std::fs::write(
        directory().join("result.json"),
        serde_json::to_vec_pretty(&json!({"success": error.is_none(), "error": error})).unwrap(),
    );
    app.exit(if error.is_none() { 0 } else { 1 });
}

pub const SCRIPT: &str = r#"
(async () => {
  const invoke = window.__TAURI_INTERNALS__.invoke;
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const request = (method, params = {}) => invoke('desktop_request', {method, params});
  try {
    for (let i = 0; i < 100 && !document.querySelector('.desktopControls'); i++) await wait(100);
    if (!document.querySelector('.desktopControls')) throw Error('Desktop controls did not render');
    const snapshot = await request('snapshot');
    if (!snapshot.messages.some(m => m.type === 'authenticated' && m.admin)) throw Error('Native transport failed');
    await wait(600);
    window.scrollTo(0, 0);
    if (document.querySelectorAll('.matrixPad').length !== 64) throw Error('Missing pad matrix');
    const header = document.querySelector('.appHeader').getBoundingClientRect();
    if (header.top < 0) throw Error('Session controls scrolled out of view');
    await invoke('smoke_checkpoint', {label: 'desktop-idle', details: {pads: 64, width: innerWidth, scrollWidth: document.documentElement.scrollWidth, headerTop: header.top}});
    await request('surface', {protocol: 1, type: 'start_experience', kind: 'show'});
    await wait(2500);
    const active = await request('snapshot');
    if (!active.messages.some(m => m.type === 'performance_frame')) throw Error('Show frames unavailable');
    await invoke('smoke_checkpoint', {label: 'desktop-show', details: {show: true}});
    await request('surface', {protocol: 1, type: 'stop_experience'});
    document.querySelector('button[aria-label="Settings"]').click();
    await wait(250);
    await invoke('smoke_checkpoint', {label: 'desktop-settings', details: {settings: !!document.querySelector('.desktopSettings')}});
    await invoke('smoke_finish', {error: null});
  } catch (error) { await invoke('smoke_finish', {error: String(error)}); }
})();
"#;
