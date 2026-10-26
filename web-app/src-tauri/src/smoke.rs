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
    if let Some(message) = &error {
        eprintln!("Native smoke test failed: {message}");
    }
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
    for (let i = 0; i < 100 && document.querySelector('.openConversations')?.getAttribute('aria-busy') === 'true'; i++) await wait(100);
    const discovery = await request('list_conversations');
    if (typeof discovery.available !== 'boolean' || !Array.isArray(discovery.conversations)) throw Error('Native discovery failed');
    if (document.querySelector('.openConversations')?.textContent.includes('Unsupported desktop request')) throw Error('Discovery rejected by native bridge');
    for (let i = 0; i < 100 && document.querySelector('.openConversations')?.getAttribute('aria-busy') === 'true'; i++) await wait(100);
    if (document.querySelector('.openConversations')?.textContent.includes('discovery is already running')) throw Error('Concurrent discovery failed');
    const snapshot = await request('snapshot');
    if (!snapshot.messages.some(m => m.type === 'authenticated' && m.admin)) throw Error('Native transport failed');
    const response = await fetch('./experiences/audio/earcon-success-none.wav');
    if (!response.ok) throw Error('Bundled audio asset is unavailable');
    const audioUrl = URL.createObjectURL(await response.blob());
    const audio = new Audio(audioUrl);
    audio.muted = true;
    let playbackError = null;
    try {
      await Promise.race([audio.play(), wait(5000).then(() => { throw Error('Playback timed out'); })]);
      await wait(300);
    } catch (error) { playbackError = String(error); }
    await invoke('smoke_checkpoint', {label: 'desktop-audio', details: {
      url: audio.src, error: playbackError, mediaError: audio.error?.message,
      code: audio.error?.code, time: audio.currentTime, ready: audio.readyState,
      wav: audio.canPlayType('audio/wav'),
    }});
    audio.pause();
    URL.revokeObjectURL(audioUrl);
    if (playbackError) throw Error(playbackError);
    await wait(600);
    window.scrollTo(0, 0);
    if (document.querySelectorAll('.matrixPad').length !== 64) throw Error('Missing pad matrix');
    const header = document.querySelector('.appHeader').getBoundingClientRect();
    if (header.top < 0) throw Error('Session controls scrolled out of view');
    await invoke('smoke_checkpoint', {label: 'desktop-idle', details: {pads: 64, width: innerWidth, scrollWidth: document.documentElement.scrollWidth, headerTop: header.top}});
    const players = [];
    const NativeAudio = window.Audio;
    window.Audio = class extends NativeAudio {
      constructor(...args) { super(...args); players.push(this); }
    };
    if ([...document.querySelectorAll('button')].some(button => button.textContent.includes('Start Show'))) throw Error('Show controls leaked into the Codex sessions view');
    const sound = document.querySelector('button[aria-label="Sound"]');
    if (!sound) throw Error('Global sound control missing');
    if (sound.getAttribute('aria-pressed') !== 'true') sound.click();
    document.querySelector('button[aria-label="Demo & Show"]').click();
    await wait(100);
    [...document.querySelectorAll('[role="menuitem"]')].find(button => button.textContent === 'Show').click();
    await wait(200);
    await wait(2500);
    const active = await request('snapshot');
    if (!active.messages.some(m => m.type === 'performance_frame')) throw Error('Show frames unavailable');
    const playingAudio = players.find(player => player.currentTime > 0 && !player.paused && !player.muted && player.volume > 0);
    await invoke('smoke_checkpoint', {label: 'desktop-show-audio', details: {
      playing: !!playingAudio, players: players.map(player => ({url: player.src, time: player.currentTime, paused: player.paused, error: player.error?.code})),
    }});
    if (!playingAudio) throw Error('The Show player did not start audible playback');
    await invoke('smoke_checkpoint', {label: 'desktop-show', details: {show: true}});
    await request('surface', {protocol: 1, type: 'stop_experience'});
    [...document.querySelectorAll('button')].find(button => button.textContent.includes('Back to live pad')).click();
    await wait(100);
    if (!document.querySelector('.selectedConversation')) throw Error('Selected conversation panel missing');
    document.querySelector('button[aria-label="Settings"]').click();
    await wait(250);
    await invoke('smoke_checkpoint', {label: 'desktop-settings', details: {settings: !!document.querySelector('.desktopSettings')}});
    await invoke('smoke_finish', {error: null});
  } catch (error) { await invoke('smoke_finish', {error: String(error)}); }
})();
"#;
