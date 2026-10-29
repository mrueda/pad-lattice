use serde_json::{json, Value};
use std::{
    collections::HashMap,
    io::{BufRead, BufReader, Read, Write},
    path::Path,
    process::{Child, ChildStdin, Command, Stdio},
    sync::{
        atomic::{AtomicU64, Ordering},
        mpsc, Arc, Mutex,
    },
    time::Duration,
};
use tauri::{AppHandle, Emitter};

type Pending = Arc<Mutex<HashMap<u64, mpsc::Sender<Result<Value, String>>>>>;

pub struct Engine {
    child: Mutex<Child>,
    input: Mutex<Option<ChildStdin>>,
    pending: Pending,
    sequence: AtomicU64,
}

pub fn allowed_method(method: &str) -> bool {
    matches!(
        method,
        "snapshot"
            | "status"
            | "settings"
            | "inspect_codex"
            | "list_conversations"
            | "attach_conversation"
            | "detach_conversation"
            | "question_status"
            | "approval_status"
            | "answer_question"
            | "lan"
            | "paired_devices"
            | "disconnect_device"
            | "revoke_device"
            | "connect_midi"
            | "disconnect_midi"
            | "attention"
            | "profile_test_start"
            | "profile_test_status"
            | "profile_test_answer"
            | "profile_test_cancel"
            | "profile_test_report"
            | "surface"
    )
}

impl Engine {
    pub fn start(app: AppHandle, executable: &Path, data: &Path) -> Result<Self, String> {
        let mut command = Command::new(executable);
        command
            .args(["service", "--settings-dir"])
            .arg(data)
            .env_remove("PYTHONPATH")
            .env_remove("PYTHONHOME")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        #[cfg(feature = "native-smoke")]
        if std::env::var_os("PAD_LATTICE_SMOKE_DIR").is_some() {
            command.arg("--socket").arg(data.join("agent.sock"));
        }
        let mut child = command
            .spawn()
            .map_err(|e| format!("Cannot start the bundled engine: {e}"))?;
        let input = child.stdin.take();
        let stdout = child.stdout.take().unwrap();
        let stderr = child.stderr.take().unwrap();
        std::thread::spawn(move || {
            // Drain diagnostics without sending native-library output through the protocol.
            let _ = std::io::copy(&mut BufReader::new(stderr), &mut std::io::sink());
        });
        let pending: Pending = Arc::new(Mutex::new(HashMap::new()));
        let waiting = pending.clone();
        let (ready_tx, ready_rx) = mpsc::channel();
        std::thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            loop {
                let mut line = String::new();
                match reader.by_ref().take(1024 * 1024 + 1).read_line(&mut line) {
                    Ok(0) | Err(_) => break,
                    Ok(_) if line.len() > 1024 * 1024 => break,
                    _ => {}
                }
                let Ok(message) = serde_json::from_str::<Value>(&line) else {
                    break;
                };
                if let Some(id) = message["id"].as_u64() {
                    if let Some(sender) = waiting.lock().unwrap().remove(&id) {
                        let result = message["error"]
                            .as_str()
                            .map(|e| Err(e.to_string()))
                            .unwrap_or_else(|| Ok(message["result"].clone()));
                        let _ = sender.send(result);
                    }
                } else {
                    match message["event"].as_str() {
                        Some("ready") => {
                            let result = if message["version"] == env!("CARGO_PKG_VERSION") {
                                Ok(())
                            } else {
                                Err("Desktop and engine versions differ. Reinstall the app."
                                    .to_string())
                            };
                            let _ = ready_tx.send(result);
                        }
                        Some("surface") => {
                            let _ = app.emit("pad-lattice-surface", &message["payload"]);
                        }
                        Some("device") => {
                            let _ = app.emit("pad-lattice-device", &message);
                        }
                        Some("attachment_disconnected") => {
                            let _ = app.emit("pad-lattice-attachment", &message);
                        }
                        Some("fatal") => {
                            let reason =
                                message["error"].as_str().unwrap_or("Local service failed");
                            let _ = ready_tx.send(Err(reason.to_string()));
                            let _ = app.emit("pad-lattice-disconnected", reason);
                        }
                        _ => {}
                    }
                }
            }
            for (_, sender) in waiting.lock().unwrap().drain() {
                let _ = sender.send(Err("The local service has stopped.".into()));
            }
            let _ = app.emit(
                "pad-lattice-disconnected",
                "The local service has stopped. Restart Pad-Lattice.",
            );
        });
        let engine = Self {
            child: Mutex::new(child),
            input: Mutex::new(input),
            pending,
            sequence: AtomicU64::new(1),
        };
        ready_rx
            .recv_timeout(Duration::from_secs(30))
            .map_err(|_| "The local service did not become ready.".to_string())??;
        Ok(engine)
    }

    pub fn request(&self, method: &str, params: Value) -> Result<Value, String> {
        if !allowed_method(method) || !params.is_object() {
            return Err("Unsupported desktop request".into());
        }
        let id = self.sequence.fetch_add(1, Ordering::Relaxed);
        let mut bytes =
            serde_json::to_vec(&json!({"id": id, "method": method, "params": params})).unwrap();
        if bytes.len() > 60 * 1024 {
            return Err("Desktop request is too large".into());
        }
        bytes.push(b'\n');
        let (sender, receiver) = mpsc::channel();
        self.pending.lock().unwrap().insert(id, sender);
        let sent = self
            .input
            .lock()
            .unwrap()
            .as_mut()
            .ok_or_else(|| "The local service has stopped.".to_string())
            .and_then(|input| input.write_all(&bytes).map_err(|e| e.to_string()));
        let result = sent.and_then(|_| {
            receiver
                .recv_timeout(Duration::from_secs(30))
                .map_err(|_| "The local service did not answer in time.".to_string())?
        });
        self.pending.lock().unwrap().remove(&id);
        result
    }

    pub fn stop(&self) {
        self.input.lock().unwrap().take();
        let mut child = self.child.lock().unwrap();
        for _ in 0..50 {
            if child.try_wait().ok().flatten().is_some() {
                return;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        let _ = child.kill();
        let _ = child.wait();
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        self.stop();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_arbitrary_process_and_filesystem_commands() {
        assert!(!allowed_method("launch_session"));
        assert!(allowed_method("list_conversations"));
        assert!(allowed_method("attach_conversation"));
        assert!(allowed_method("detach_conversation"));
        for method in ["exec", "shell", "read_file", "write_file", ""] {
            assert!(!allowed_method(method));
        }
    }
}
